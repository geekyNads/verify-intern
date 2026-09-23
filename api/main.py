"""VerifyIntern API.

Endpoints:
  GET  /health                -> dataset counts
  GET  /register              -> the whole dataset (what the static UI loads)
  GET  /patterns              -> scam patterns only
  GET  /employers             -> flagged employer records only
  GET  /lookup?query=         -> flagged employers/domains matching a query
  POST /check                 -> pattern-match free text (an offer/email body)
  POST /report                -> submit a suspected scam for human review

This API is OPTIONAL. The site in /web runs the identical rules client-side
(see web/classifier.js) so students can use the tool with nothing installed.
The API exists for integrators: university placement portals, bots, bulk
checks.

Nothing here auto-publishes a community report into the canonical dataset —
per ARCHITECTURE.md, /report only ever writes to data/_pending/ for review.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .classifier import get_dataset
from .schemas import (
    CheckRequest,
    CheckResult,
    FlaggedEmployer,
    LookupResult,
    Register,
    ReportAck,
    ReportSubmission,
    ScamPattern,
)

app = FastAPI(
    title="VerifyIntern API",
    description="Open, source-backed lookup for suspected fake internship/employer offers.",
    version="0.1.0",
)

# Permissive CORS for v0 since the frontend is a static page that may be
# served from anywhere (file://, GitHub Pages, localhost). Tighten before
# any production deployment that isn't just "run it yourself".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

PENDING_DIR = Path(__file__).resolve().parent.parent / "data" / "_pending"
PENDING_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict:
    ds = get_dataset()
    return {
        "status": "ok",
        "flagged_employers": len(ds.flagged_employers),
        "scam_patterns": len(ds.scam_patterns),
    }


@app.get("/lookup", response_model=LookupResult)
def lookup(query: str = Query(..., min_length=1, description="Company name or domain")) -> LookupResult:
    ds = get_dataset()
    matches = ds.find_employers(query)
    return LookupResult(query=query, matches=matches, found=bool(matches))


@app.post("/check", response_model=CheckResult)
def check(payload: CheckRequest) -> CheckResult:
    """Pattern-match a pasted offer. The request body is not stored anywhere."""
    return get_dataset().check_text(payload.text)


@app.get("/register", response_model=Register)
def register() -> Register:
    """The whole public dataset in one response — this is what the static
    frontend loads when it is pointed at a running API instead of at the
    JSONL files it ships with."""
    ds = get_dataset()
    return Register(flagged_employers=ds.flagged_employers, scam_patterns=ds.scam_patterns)


@app.get("/patterns", response_model=list[ScamPattern])
def patterns() -> list[ScamPattern]:
    return get_dataset().scam_patterns


@app.get("/employers", response_model=list[FlaggedEmployer])
def employers() -> list[FlaggedEmployer]:
    return get_dataset().flagged_employers


@app.post("/report", response_model=ReportAck)
def report(submission: ReportSubmission) -> ReportAck:
    record_id = f"pending_{uuid.uuid4().hex[:10]}"
    candidate = {
        "id": record_id,
        "company_name": submission.company_name,
        "aliases": [],
        "domains": [submission.domain] if submission.domain else [],
        "impersonating": None,
        "pattern_ids": [],
        "status": "reported",
        "sources": (
            [
                {
                    "type": "community_report",
                    "title": f"Community report: {submission.reason[:80]}",
                    "url": submission.evidence_url or "",
                    "date": date.today().isoformat(),
                }
            ]
        ),
        "summary": submission.reason,
        "date_added": datetime.now(timezone.utc).isoformat(),
        "last_reviewed": "",
        "_needs_review": True,
        "_submitter_contact": submission.submitter_contact,
    }

    out_path = PENDING_DIR / f"{record_id}.json"
    out_path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")

    return ReportAck(
        id=record_id,
        status="queued_for_review",
        message=(
            "Thanks — this has been queued for human review and is not yet part of the "
            "public dataset. It won't show up in lookups until a maintainer confirms it "
            "has a verifiable source."
        ),
    )
