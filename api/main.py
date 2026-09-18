"""VerifyIntern API.

Endpoints:
  GET  /lookup?query=       -> known flagged employers/domains matching query
  POST /check                -> pattern-match free text (an offer/email body)
  POST /report                -> submit a suspected scam for human review
  GET  /health

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
from .schemas import CheckResult, LookupResult, ReportAck, ReportSubmission

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


class CheckRequest(dict):
    """Accepts {"text": "..."} — kept as a thin wrapper to avoid an extra import cycle."""


@app.post("/check", response_model=CheckResult)
def check(payload: dict) -> CheckResult:
    text = payload.get("text", "")
    ds = get_dataset()
    return ds.check_text(text)


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
