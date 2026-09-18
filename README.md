# VerifyIntern (working name)

**An open, community-maintained legitimacy checker for internship and job offers.**

Students and early-career job seekers get flooded with fake internship offers,
"registration fee" scams, and impersonated-employer schemes. VerifyIntern lets
anyone paste an offer (company name, email domain, offer letter text, payment
request, etc.) and get a legitimacy signal, backed by a transparent, open
dataset of known scam patterns — not a black-box "trust us" score.

## Why this is open source

Verification tools live or die on trust, and trust requires people being able
to see *why* something was flagged. A closed product that says "this is a
scam, trust me" is a harder sell than a repo where anyone can read the rules,
audit the data sources, and submit a correction. The dataset itself — verified
scam patterns, fake-employer domains, known offer-letter templates — is a
public good that gets stronger the more people contribute to it, the same way
crowdsourced threat-intel lists or ad-blocker filter lists do.

## What it does (v0 scope)

1. **Lookup**: check a company name / domain / email against known
   scam-employer records.
2. **Pattern match**: flag common scam markers in offer text (upfront
   "registration" or "training" fees, personal-account payment requests,
   generic free-email domains posing as corporate recruiters, urgency
   language, unverifiable physical address, etc.).
3. **Source-backed advisories**: surface matching entries from public advisory
   sources (AICTE, university placement cells, IIT-Roorkee-style circulars,
   Reddit/Substack scam-report threads) with a link back to the original.
4. **Community flagging**: anyone can submit a new suspected scam report
   through a structured form/PR; reports are reviewed before merging into the
   canonical dataset.

## What it explicitly does NOT do (v0)

- No automated "definitely a scam" verdicts — it surfaces evidence and a
  confidence signal, and always shows its sources.
- No accusing a *named individual* of fraud without a corroborating public
  source; flags attach to companies/domains/patterns, not to people.
- No scraping or reproducing copyrighted advisory PDFs wholesale — we extract
  structured facts (company name, date, issuing body, pattern type) and link
  to the original document.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run the tests
python -m pytest api/tests -v

# run the API (loads /data on startup)
python -m uvicorn api.main:app --reload --port 8000

# in another terminal, serve the frontend and open it in a browser
python -m http.server 8080 --directory web
# then visit http://127.0.0.1:8080/index.html
```

The frontend talks to the API at `http://127.0.0.1:8000` by default — that's
editable in the input field at the top of the page if you're running the
API somewhere else.

### Add a new verified scam report (maintainer flow)

```bash
# 1. ingest a candidate from a source (writes to data/_pending/, not canonical yet)
python -m scraper.sources.careers360_advisories \
  --url "https://example.com/advisory" \
  --company-name "Example Corp" \
  --summary "One or two sentences in your own words." \
  --pattern-ids sp_0001 --skip-fetch

# 2. review it
python -m scraper.review_queue list
python -m scraper.review_queue show <id>

# 3. approve (or reject) — approving with --confirm sets status to "confirmed"
python -m scraper.review_queue approve <id> --confirm
```

## Repo layout

```
/data/            canonical scam-pattern & flagged-employer dataset (see DATA_SCHEMA.md)
/scraper/         ingestion scripts for public advisory sources
/api/             lookup + classification service
/web/             minimal frontend for lookup + submitting reports
/docs/            ARCHITECTURE.md, DATA_SCHEMA.md, CONTRIBUTING.md
CLAUDE.md         instructions for AI coding agents working in this repo
```

## Roadmap

- **Weekend 1**: dataset schema + seed data from 2-3 public sources, basic
  domain/company lookup CLI.
- **Weeks 2-4**: pattern-matching classifier for offer-letter text, minimal
  web UI, submission form with review queue.
- **Post-launch**: browser extension, verified-employer badge API (this is
  the seam where a commercial layer could attach later, e.g. premium checks
  for university career centers — but the core dataset and lookup stay open).

## License

Code: MIT (see `LICENSE`). Dataset: CC BY-SA 4.0 (see `DATA_LICENSE`) —
share-alike, so downstream commercial forks must keep their derived data
open too.

## Status

v0 is built and working end to end: seed dataset (2 flagged-employer records,
6 scam patterns, all sourced from public AICTE/IIT Roorkee advisories and
press coverage), a FastAPI backend (`/lookup`, `/check`, `/report`) with a
rule-based, source-citing classifier and a passing test suite, a scraper +
human review queue for adding new records safely, and a static web UI. See
Quickstart above to run it.
