"""Human-in-the-loop review queue for candidate records in data/_pending/.

    python -m scraper.review_queue list
    python -m scraper.review_queue show fe_pending_abc123
    python -m scraper.review_queue approve fe_pending_abc123
    python -m scraper.review_queue reject fe_pending_abc123 --reason "no verifiable source"

`approve` validates the record against the required schema fields (see
docs/DATA_SCHEMA.md), refuses to approve anything with an empty `sources`
list or a `status` of "confirmed" set by a script rather than a human, then
appends it to data/flagged_employers/flagged_employers.jsonl and removes it
from the pending queue.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING_DIR = ROOT / "data" / "_pending"
CANONICAL_PATH = ROOT / "data" / "flagged_employers" / "flagged_employers.jsonl"

REQUIRED_FIELDS = {
    "id",
    "company_name",
    "aliases",
    "domains",
    "impersonating",
    "pattern_ids",
    "status",
    "sources",
    "summary",
    "date_added",
    "last_reviewed",
}


def _pending_files() -> list[Path]:
    return sorted(PENDING_DIR.glob("*.json"))


def cmd_list(_: argparse.Namespace) -> None:
    files = _pending_files()
    if not files:
        print("Pending queue is empty.")
        return
    for f in files:
        record = json.loads(f.read_text(encoding="utf-8"))
        print(f"{record.get('id', f.stem):<24} {record.get('company_name', '?')}")


def cmd_show(args: argparse.Namespace) -> None:
    path = PENDING_DIR / f"{args.record_id}.json"
    if not path.exists():
        print(f"No pending record with id {args.record_id}", file=sys.stderr)
        sys.exit(1)
    print(path.read_text(encoding="utf-8"))


def _validate(record: dict) -> list[str]:
    problems = []
    missing = REQUIRED_FIELDS - record.keys()
    if missing:
        problems.append(f"missing fields: {sorted(missing)}")
    if not record.get("sources"):
        problems.append("sources list is empty — every record needs a citable source")
    for src in record.get("sources", []):
        if not src.get("url") and src.get("type") != "community_report":
            problems.append("a non-community-report source has no url")
    if record.get("status") == "confirmed":
        problems.append(
            "status is already 'confirmed' — a human reviewer must set this explicitly "
            "with --confirm, scripts should only ever produce 'reported'"
        )
    return problems


def cmd_approve(args: argparse.Namespace) -> None:
    path = PENDING_DIR / f"{args.record_id}.json"
    if not path.exists():
        print(f"No pending record with id {args.record_id}", file=sys.stderr)
        sys.exit(1)

    record = json.loads(path.read_text(encoding="utf-8"))
    problems = _validate(record)
    if problems and not args.force:
        print("Refusing to approve — fix these first (or pass --force to override):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    if args.confirm:
        record["status"] = "confirmed"
    record.pop("_needs_review", None)
    record.pop("_submitter_contact", None)

    CANONICAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CANONICAL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    path.unlink()
    print(f"Approved {args.record_id} -> merged into {CANONICAL_PATH.relative_to(ROOT)}")


def cmd_reject(args: argparse.Namespace) -> None:
    path = PENDING_DIR / f"{args.record_id}.json"
    if not path.exists():
        print(f"No pending record with id {args.record_id}", file=sys.stderr)
        sys.exit(1)
    path.unlink()
    print(f"Rejected and removed {args.record_id}. Reason: {args.reason or '(none given)'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    p_show = sub.add_parser("show")
    p_show.add_argument("record_id")
    p_show.set_defaults(func=cmd_show)

    p_approve = sub.add_parser("approve")
    p_approve.add_argument("record_id")
    p_approve.add_argument("--confirm", action="store_true", help="Mark status as 'confirmed' instead of 'reported'")
    p_approve.add_argument("--force", action="store_true", help="Approve despite validation problems")
    p_approve.set_defaults(func=cmd_approve)

    p_reject = sub.add_parser("reject")
    p_reject.add_argument("record_id")
    p_reject.add_argument("--reason", default=None)
    p_reject.set_defaults(func=cmd_reject)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
