"""Dataset loading + rule-based classification.

Deliberately NOT a black-box ML model (see CLAUDE.md: "Classification logic
should be rule-based / pattern-matching first ... this keeps every result
explainable"). Every match returned by this module points back to a specific
record in /data, with its sources, so the API and UI can always show *why*
something was flagged.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .schemas import CheckResult, FlaggedEmployer, MatchedPattern, ScamPattern

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FLAGGED_EMPLOYERS_PATH = DATA_DIR / "flagged_employers" / "flagged_employers.jsonl"
SCAM_PATTERNS_PATH = DATA_DIR / "scam_patterns" / "scam_patterns.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


@dataclass
class Dataset:
    flagged_employers: list[FlaggedEmployer]
    scam_patterns: list[ScamPattern]

    @classmethod
    def load(cls) -> "Dataset":
        employers = [FlaggedEmployer(**r) for r in _load_jsonl(FLAGGED_EMPLOYERS_PATH)]
        patterns = [ScamPattern(**r) for r in _load_jsonl(SCAM_PATTERNS_PATH)]
        return cls(flagged_employers=employers, scam_patterns=patterns)

    def find_employers(self, query: str) -> list[FlaggedEmployer]:
        q = query.strip().lower()
        if not q:
            return []
        matches = []
        for emp in self.flagged_employers:
            haystack = [emp.company_name.lower(), *[a.lower() for a in emp.aliases]]
            domains = [d.lower() for d in emp.domains]
            if any(q in h or h in q for h in haystack) or any(q == d or q in d for d in domains):
                matches.append(emp)
        return matches

    def pattern_by_id(self, pattern_id: str) -> ScamPattern | None:
        for p in self.scam_patterns:
            if p.id == pattern_id:
                return p
        return None

    def check_text(self, text: str) -> CheckResult:
        text_lower = text.lower()
        matched: list[MatchedPattern] = []
        for pattern in self.scam_patterns:
            hits = [
                hint
                for hint in pattern.detection_hints
                if re.search(re.escape(hint.lower()), text_lower)
            ]
            if hits:
                matched.append(MatchedPattern(pattern=pattern, matched_hints=hits))

        # Also surface any flagged employer/domain named directly in the text.
        matched_employers = [
            emp
            for emp in self.flagged_employers
            if emp.company_name.lower() in text_lower
            or any(d.lower() in text_lower for d in emp.domains)
        ]

        high_severity_hits = sum(1 for m in matched if m.pattern.severity == "high")
        if matched_employers or high_severity_hits >= 2:
            confidence = "high"
        elif high_severity_hits == 1 or len(matched) >= 2:
            confidence = "medium"
        elif matched:
            confidence = "low"
        else:
            confidence = "none"

        if confidence == "none":
            explanation = (
                "No known scam patterns or flagged employers matched this text. "
                "This is not a guarantee the offer is legitimate — it only means "
                "nothing in the current dataset matched. Always verify independently."
            )
        else:
            names = ", ".join(m.pattern.name for m in matched) or "none"
            emp_names = ", ".join(e.company_name for e in matched_employers)
            explanation = f"Matched pattern(s): {names}."
            if emp_names:
                explanation += f" Matched flagged record(s): {emp_names}."

        return CheckResult(
            matched_patterns=matched,
            matched_employers=matched_employers,
            confidence=confidence,
            explanation=explanation,
        )


_dataset: Dataset | None = None


def get_dataset() -> Dataset:
    """Lazily load and cache the dataset. Call reload() in tests/dev after editing /data."""
    global _dataset
    if _dataset is None:
        _dataset = Dataset.load()
    return _dataset


def reload() -> Dataset:
    global _dataset
    _dataset = Dataset.load()
    return _dataset
