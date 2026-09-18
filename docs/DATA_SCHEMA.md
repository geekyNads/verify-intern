# Data Schema

All canonical data lives in `/data` as JSON Lines (one JSON object per line).
Two record types: `flagged_employers` and `scam_patterns`.

## `flagged_employers/*.jsonl`

```jsonc
{
  "id": "fe_2024_0001",                 // stable id, never reused
  "company_name": "Example Corp",
  "aliases": ["Example Corporation Pvt Ltd"],
  "domains": ["example-corp-careers.com"],   // NOT the real company's domain if impersonated
  "impersonating": "example.com",        // set if this is a lookalike/impersonation of a real company, else null
  "pattern_ids": ["sp_0003", "sp_0007"], // links into scam_patterns.jsonl
  "status": "confirmed",                 // "confirmed" | "reported" | "disputed"
  "sources": [
    {
      "type": "official_advisory",       // official_advisory | publication | community_report
      "title": "AICTE advisory on fake internship offers, March 2024",
      "url": "https://example.gov.in/advisory/123",
      "date": "2024-03-14"
    }
  ],
  "summary": "Short, original-wording paraphrase of what the source says. Not a copied excerpt.",
  "date_added": "2024-03-20",
  "last_reviewed": "2024-03-20"
}
```

## `scam_patterns/*.jsonl`

```jsonc
{
  "id": "sp_0003",
  "name": "Upfront registration/training fee",
  "description": "Offer requires payment before onboarding, framed as a refundable deposit, training kit fee, or registration charge.",
  "detection_hints": [
    "regex or keyword hints used by /api classifier, e.g. ['registration fee', 'refundable deposit', 'training kit charge']"
  ],
  "severity": "high",                   // low | medium | high
  "sources": [ /* same shape as above */ ]
}
```

## Status field semantics (important — this is a defamation-risk control)

- `reported`: a single, uncorroborated community submission. Shown to users
  with a clear "unverified community report" label.
- `confirmed`: at least one official advisory or publication source, or two+
  independent community reports describing the same pattern/company.
- `disputed`: the flagged party has contested it; shown with both the flag
  and the dispute context rather than removed outright, unless the flag is
  found to be false, in which case it's removed with a note in commit
  history.

## Rules for every record

- `sources` must never be empty.
- `summary`/`description` must be original paraphrase, not copied text —
  see CLAUDE.md rule 3.
- Records about individuals are out of scope; `flagged_employers` only
  covers companies, domains, and recruiting patterns.
- Any script that writes into `/data/_pending/` for review must follow this
  exact schema so the review queue can validate automatically before a human
  looks at it.
