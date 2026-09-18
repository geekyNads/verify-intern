# Contributing

This project is only as good as its dataset, so the most valuable
contribution most people can make is **reporting a suspected scam** — you
don't need to write code.

## Reporting a suspected scam internship/employer

1. Use the in-app "Report" form if it's live, or open an issue using the
   `scam-report` template.
2. Include: company/domain name, what made it suspicious, and — critically —
   a link to evidence (a screenshot, an advisory, a forum thread, a news
   article). Reports without any linkable evidence go into `reported` status
   only and may not surface prominently until corroborated.
3. Do not name a private individual as the fraudster unless a public source
   already does.

## Contributing code

1. Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, and `docs/DATA_SCHEMA.md` first
   — most rejected PRs are rejected for violating the sourcing/transparency
   rules there, not for code style.
2. Fork, branch, small focused commits.
3. If your change touches `/data`, it must go through `/data/_pending/` and
   the review checklist in the PR template — no direct edits to canonical
   files.
4. If your change touches `/api` classification logic, add a test pinning
   expected output for one known-scam and one known-legitimate example.

## Adding a new ingestion source

1. Confirm the source is public and you're not violating its terms of
   service by scraping it.
2. Add it to the "Sources" table in `docs/ARCHITECTURE.md` with its
   reliability tier before writing the scraper.
3. Scraper output goes to `/data/_pending/`, never directly to canonical
   files, and must extract structured facts only — no verbatim copying of
   source text (see CLAUDE.md rule 3).

## Code of conduct

Be direct, be kind, assume good faith on scam reports (people submitting
them are often the ones who almost got scammed) — and hold a high bar for
evidence before anything gets marked `confirmed` against a real company.
