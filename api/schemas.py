"""Pydantic models for the VerifyIntern API.

Kept deliberately explicit (no bare dicts flowing through the API) so that
every response has a documented shape and every classification result is
forced to carry its supporting sources, per CLAUDE.md rule 4:
"Every classifier output must show its reasoning."
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["official_advisory", "publication", "community_report"]
RecordStatus = Literal["confirmed", "reported", "disputed"]
Severity = Literal["low", "medium", "high"]


class Source(BaseModel):
    type: SourceType
    title: str
    url: str
    date: str


class FlaggedEmployer(BaseModel):
    id: str
    company_name: str
    aliases: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    impersonating: str | None = None
    pattern_ids: list[str] = Field(default_factory=list)
    status: RecordStatus
    sources: list[Source]
    summary: str
    date_added: str
    last_reviewed: str


class ScamPattern(BaseModel):
    id: str
    name: str
    description: str
    detection_hints: list[str]
    severity: Severity
    sources: list[Source]


class LookupResult(BaseModel):
    query: str
    matches: list[FlaggedEmployer]
    found: bool


class Register(BaseModel):
    """The whole public dataset, as served to the static frontend."""

    flagged_employers: list[FlaggedEmployer]
    scam_patterns: list[ScamPattern]


class MatchedPattern(BaseModel):
    pattern: ScamPattern
    matched_hints: list[str]


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The offer email, message or letter to check")


class CheckResult(BaseModel):
    matched_patterns: list[MatchedPattern]
    matched_employers: list[FlaggedEmployer]
    confidence: Literal["none", "low", "medium", "high"]
    score: int = Field(0, ge=0, le=100, description="0-100 display score; `confidence` is authoritative")
    explanation: str
    advice: list[str] = Field(default_factory=list, description="General verification steps, not record-specific")


class ReportSubmission(BaseModel):
    company_name: str
    domain: str | None = None
    reason: str = Field(..., min_length=10)
    evidence_url: str | None = None
    submitter_contact: str | None = None


class ReportAck(BaseModel):
    id: str
    status: Literal["queued_for_review"]
    message: str
