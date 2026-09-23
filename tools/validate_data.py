#!/usr/bin/env python3
"""Check the dataset against the rules in docs/DATA_SCHEMA.md and CLAUDE.md.

    python tools/validate_data.py

Runs on every pull request. The point is that nobody — human or agent — can
quietly add an unsourced accusation to the register: a record with no source,
a duplicate id, a dangling pattern reference or a malformed date fails the
build. Standard library only, so it runs anywhere.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EMPLOYERS = DATA / "flagged_employers" / "flagged_employers.jsonl"
PATTERNS = DATA / "scam_patterns" / "scam_patterns.jsonl"
PENDING = DATA / "_pending"

SOURCE_TYPES = {"official_advisory", "publication", "community_report"}
STATUSES = {"confirmed", "reported", "disputed"}
SEVERITIES = {"low", "medium", "high"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

EMPLOYER_FIELDS = {
    "id", "company_name", "aliases", "domains", "impersonating", "pattern_ids",
    "status", "sources", "summary", "date_added", "last_reviewed",
}
PATTERN_FIELDS = {"id", "name", "description", "detection_hints", "severity", "sources"}

problems: list[str] = []


def fail(where: str, message: str) -> None:
    problems.append(f"{where}: {message}")


def load_jsonl(path: Path) -> list[dict]:
    records = []
    if not path.exists():
        fail(path.name, "file is missing")
        return records
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"{path.name}:{lineno}", f"not valid JSON ({exc.msg})")
            continue
        if not isinstance(record, dict):
            fail(f"{path.name}:{lineno}", "each line must be a JSON object")
            continue
        records.append(record)
    return records


def check_sources(where: str, record: dict) -> None:
    sources = record.get("sources")
    if not isinstance(sources, list) or not sources:
        fail(where, "has no sources — every record must cite a public source (CLAUDE.md rule 1)")
        return
    for i, src in enumerate(sources):
        at = f"{where} source[{i}]"
        if not isinstance(src, dict):
            fail(at, "must be an object")
            continue
        for field in ("type", "title", "url", "date"):
            if field not in src:
                fail(at, f"missing '{field}'")
        if src.get("type") not in SOURCE_TYPES:
            fail(at, f"type must be one of {sorted(SOURCE_TYPES)}, got {src.get('type')!r}")
        if src.get("type") != "community_report" and not src.get("url"):
            fail(at, "a non-community-report source needs a url a reviewer can open")
        url = src.get("url") or ""
        if url and not url.startswith(("http://", "https://")):
            fail(at, f"url should be an http(s) link, got {url!r}")
        if src.get("date") and not DATE_RE.match(str(src["date"])):
            fail(at, f"date must be YYYY-MM-DD, got {src['date']!r}")


def check_fields(where: str, record: dict, required: set[str]) -> None:
    missing = required - record.keys()
    if missing:
        fail(where, f"missing fields: {sorted(missing)}")
    unknown = record.keys() - required
    if unknown:
        fail(where, f"unexpected fields (typo?): {sorted(unknown)}")


def main() -> int:
    patterns = load_jsonl(PATTERNS)
    employers = load_jsonl(EMPLOYERS)

    pattern_ids: set[str] = set()
    for p in patterns:
        where = f"scam_patterns/{p.get('id', '?')}"
        check_fields(where, p, PATTERN_FIELDS)
        check_sources(where, p)
        pid = p.get("id", "")
        if pid in pattern_ids:
            fail(where, "duplicate id")
        pattern_ids.add(pid)
        if not re.match(r"^sp_\d{4}$", pid):
            fail(where, "id should look like sp_0001")
        if p.get("severity") not in SEVERITIES:
            fail(where, f"severity must be one of {sorted(SEVERITIES)}")
        hints = p.get("detection_hints")
        if not isinstance(hints, list) or not hints:
            fail(where, "needs at least one detection hint")
        else:
            for h in hints:
                if not isinstance(h, str) or len(h.strip()) < 3:
                    fail(where, f"detection hint {h!r} is too short to be safe — it will match everything")

    employer_ids: set[str] = set()
    for e in employers:
        where = f"flagged_employers/{e.get('id', '?')}"
        check_fields(where, e, EMPLOYER_FIELDS)
        check_sources(where, e)
        eid = e.get("id", "")
        if eid in employer_ids:
            fail(where, "duplicate id")
        employer_ids.add(eid)
        if e.get("status") not in STATUSES:
            fail(where, f"status must be one of {sorted(STATUSES)}")
        if not str(e.get("company_name", "")).strip():
            fail(where, "company_name is empty")
        if not str(e.get("summary", "")).strip():
            fail(where, "summary is empty — a reader needs to know why this is listed")
        for pid in e.get("pattern_ids", []) or []:
            if pid not in pattern_ids:
                fail(where, f"references unknown pattern {pid!r}")
        for field in ("date_added",):
            if e.get(field) and not DATE_RE.match(str(e[field])):
                fail(where, f"{field} must be YYYY-MM-DD, got {e[field]!r}")
        for d in e.get("domains", []) or []:
            if not isinstance(d, str) or "." not in d or " " in d:
                fail(where, f"{d!r} does not look like a domain")
            if isinstance(d, str) and d.startswith(("http://", "https://")):
                fail(where, f"store the bare domain, not a URL: {d!r}")

    if PENDING.exists():
        for f in sorted(PENDING.glob("*.json")):
            try:
                record = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                fail(f"_pending/{f.name}", f"not valid JSON ({exc.msg})")
                continue
            if record.get("status") == "confirmed":
                fail(
                    f"_pending/{f.name}",
                    "a pending record cannot already be 'confirmed' — a human sets that on approval",
                )

    if problems:
        print(f"Dataset validation failed ({len(problems)} problem(s)):\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nSee docs/DATA_SCHEMA.md for the schema and CLAUDE.md for the sourcing rules.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Dataset is valid: {len(employers)} flagged employer record(s), "
        f"{len(patterns)} scam pattern(s), every one with a citable source."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
