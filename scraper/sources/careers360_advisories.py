"""Ingestion script for careers360.com advisory/warning articles about fake
internships, recruitment, or institute impersonation.

This does NOT write directly to the canonical dataset. It writes a
*candidate* record to data/_pending/, following the exact schema in
docs/DATA_SCHEMA.md, for a human to review (see ARCHITECTURE.md: "Review
queue"). Per CLAUDE.md rule 3, it stores a short original-wording summary,
never a copied excerpt of the article.

Usage:
    python -m scraper.sources.careers360_advisories \\
        --url "https://news.careers360.com/..." \\
        --company-name "Example Corp" \\
        --impersonating "IIT Roorkee" \\
        --pattern-ids sp_0004 \\
        --summary "One or two sentences, in your own words, of what the article says."

This is intentionally a human-in-the-loop CLI rather than an auto-summarizer:
turning a news article into a "confirmed scam" record is exactly the kind of
step that should not be fully automated (see CLAUDE.md rule 1 and 2).
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

PENDING_DIR = Path(__file__).resolve().parents[2] / "data" / "_pending"


def fetch_title(url: str, timeout: int = 10) -> str | None:
    """Best-effort fetch of the page title, just so the reviewer can sanity
    check the URL resolves to something real before merging. Never stores
    page body text — see module docstring."""
    try:
        req = Request(url, headers={"User-Agent": "verifyintern-scraper/0.1"})
        with urlopen(req, timeout=timeout) as resp:
            html = resp.read(200_000).decode("utf-8", errors="ignore")
        start = html.lower().find("<title>")
        end = html.lower().find("</title>")
        if start != -1 and end != -1:
            return html[start + 7 : end].strip()
    except Exception as exc:  # noqa: BLE001 - best effort only
        print(f"warning: could not fetch page title ({exc})", file=sys.stderr)
    return None


def build_candidate(
    *,
    url: str,
    company_name: str,
    summary: str,
    impersonating: str | None,
    pattern_ids: list[str],
    domains: list[str],
    published_date: str,
) -> dict:
    return {
        "id": f"fe_pending_{uuid.uuid4().hex[:10]}",
        "company_name": company_name,
        "aliases": [],
        "domains": domains,
        "impersonating": impersonating,
        "pattern_ids": pattern_ids,
        "status": "reported",  # never auto-set to "confirmed" — see DATA_SCHEMA.md
        "sources": [
            {
                "type": "official_advisory",
                "title": f"careers360 coverage: {company_name}",
                "url": url,
                "date": published_date,
            }
        ],
        "summary": summary,
        "date_added": date.today().isoformat(),
        "last_reviewed": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--summary", required=True, help="Original-wording paraphrase, not a copied excerpt")
    parser.add_argument("--impersonating", default=None)
    parser.add_argument("--pattern-ids", nargs="*", default=[])
    parser.add_argument("--domains", nargs="*", default=[])
    parser.add_argument("--published-date", default=date.today().isoformat())
    parser.add_argument("--skip-fetch", action="store_true", help="Skip live title fetch (offline/sandbox mode)")
    args = parser.parse_args()

    if not args.skip_fetch:
        title = fetch_title(args.url)
        if title:
            print(f"Fetched page title (sanity check only, not stored): {title}")

    candidate = build_candidate(
        url=args.url,
        company_name=args.company_name,
        summary=args.summary,
        impersonating=args.impersonating,
        pattern_ids=args.pattern_ids,
        domains=args.domains,
        published_date=args.published_date,
    )

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PENDING_DIR / f"{candidate['id']}.json"
    out_path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
    print(f"Wrote candidate record to {out_path}")
    print("This is NOT yet in the canonical dataset — a maintainer must review it (see CONTRIBUTING.md).")


if __name__ == "__main__":
    main()
