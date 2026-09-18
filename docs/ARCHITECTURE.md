# Architecture

## Overview

```
                ┌─────────────┐
  public        │  scraper/   │  ingests advisories, forum threads,
  sources ─────>│  ingestion  │  news, structures into candidate records
                └──────┬──────┘
                       │  candidate records (unreviewed)
                       v
                ┌─────────────┐
                │ review queue │  human reviews before merge
                └──────┬──────┘
                       │  approved records
                       v
                ┌─────────────┐
                │   /data      │  canonical JSONL dataset
                │ (versioned)  │  (flagged_employers, scam_patterns)
                └──────┬──────┘
                       │
                       v
                ┌─────────────┐        ┌─────────────┐
                │   api/       │<──────>│   web/       │
                │ lookup +     │        │ lookup UI +  │
                │ classifier   │        │ submit form  │
                └─────────────┘        └─────────────┘
```

## Components

### `/scraper`
One script per source (e.g. `aicte_advisories.py`, `reddit_scam_reports.py`,
`substack_digests.py`). Each script:
- Fetches from an allow-listed source.
- Extracts structured facts only (see DATA_SCHEMA.md) — never stores raw
  copyrighted text, only short paraphrases and a link back to the source.
- Writes to `/data/_pending/` as candidate records, never directly to the
  canonical dataset.

### Review queue
A lightweight process (initially: just PRs against `/data/_pending/` with a
checklist template) where a human confirms:
- The source is real and the link resolves.
- The record doesn't name a private individual without a public source doing
  so already.
- The pattern/company classification is reasonable.

Approved records move from `/data/_pending/` into `/data/flagged_employers/`
or `/data/scam_patterns/`.

### `/data`
Canonical, versioned dataset. This is the actual asset. JSONL, one file per
category, schema in `DATA_SCHEMA.md`. Changes go through normal git history
so the provenance of every record is auditable.

### `/api`
Thin service exposing:
- `GET /lookup?domain=` or `?company=` — returns matching flagged-employer
  records with sources.
- `POST /check` — takes offer text, runs pattern matching against
  `/data/scam_patterns`, returns matched patterns + confidence + sources.
- `POST /report` — accepts a community submission, writes to
  `/data/_pending/`, does not auto-merge.

Classification logic should be rule-based / pattern-matching first, not a
model call — this keeps every result explainable ("flagged because it
matches pattern X, source Y") which is the whole point of doing this in the
open. If a ML classifier is added later, it must run alongside the
rule-based layer and its output must still cite matched rules/records, not
replace them with an opaque score.

### `/web`
Minimal UI: a search/paste box, results with sources shown inline, and a
"report a suspected scam" form that posts to `/api/report`.

## Sources (reliability tiers)

| Tier | Examples | Notes |
|------|----------|-------|
| Official advisory | AICTE circulars, university placement cell notices | Highest trust, cite directly |
| Established publication | Reputable news coverage of a scam | High trust |
| Community report | Reddit threads, Substack posts | Useful for early signal, requires corroboration before "confirmed" status; stored as "reported" not "confirmed" until a second source or repeated pattern appears |

## Open questions to resolve before public launch

- Legal review of dataset license (MIT code / CC BY-SA data, per README) and
  defamation-risk review of the "flagged employer" naming policy.
- Rate limiting / abuse prevention on `/api/report` to stop the report queue
  itself being used to maliciously flag real employers.
- Whether "confirmed" vs "reported" status is shown differently in the UI
  (it should be — see DATA_SCHEMA.md `status` field).
