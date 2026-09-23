# Contributing

This project is only as good as its dataset, so the most valuable
contribution most people can make is **reporting a suspected scam** — you
don't need to write code.

## Reporting a suspected scam internship/employer

You do not need a local copy of anything, and you do not need to understand
the code. Two ways in:

- Use the **Report a scam** form on the site. It opens a pre-filled GitHub
  issue for you.
- Or open an issue directly with the **Report a suspected scam** template.

What makes a report usable:
1. Company or domain name, what they asked you for, and what made it look
   wrong.
2. A link to evidence — a screenshot, an advisory, a forum thread, a news
   article. Reports with no linkable evidence stay in `reported` status and
   may never be promoted to `confirmed`.
3. No private individual named as the fraudster unless a public source has
   already done so. Flags attach to companies, domains and patterns.
4. Your own personal details removed. Issues are public.

### Reviewing a report (maintainers)

Open the source link and confirm it says what the report claims. Then add the
record — for a one-line addition you can use GitHub's own file editor in the
browser, no clone required:

1. Open `data/flagged_employers/flagged_employers.jsonl`, press the pencil icon.
2. Add one JSON object on its own line, following `docs/DATA_SCHEMA.md`.
3. Commit to a new branch and open a pull request.

CI validates the schema, the sourcing rules and the classifier on every pull
request, so a malformed or unsourced record fails before it can be merged.

## Contributing code

1. Read `CLAUDE.md`, `docs/ARCHITECTURE.md`, and `docs/DATA_SCHEMA.md` first
   — most rejected PRs are rejected for violating the sourcing/transparency
   rules there, not for code style.
2. Fork, branch, small focused commits.
3. If your change touches `/data`, it must go through `/data/_pending/` and
   the review checklist in the PR template — no direct edits to canonical
   files.
4. If your change touches classification logic, change **both**
   `api/classifier.py` and `web/classifier.js` — the browser is what students
   actually use, and CI fails if the two disagree. Add a case to
   `tests/fixtures/classifier_cases.json` covering one known-scam and one
   known-legitimate example.

Before opening a PR:

```bash
python tools/validate_data.py
python -m pytest api/tests -q
node tools/check_parity.cjs
```

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
