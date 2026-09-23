"""Dataset loading + rule-based classification.

Deliberately NOT a black-box ML model (see CLAUDE.md: "Classification logic
should be rule-based / pattern-matching first ... this keeps every result
explainable"). Every match returned by this module points back to a specific
record in /data, with its sources, so the API and UI can always show *why*
something was flagged.

This module is mirrored in JavaScript at `web/classifier.js` so the static
site can run offline with no backend. The two implementations must stay in
sync — `tests/fixtures/classifier_cases.json` is run through both in CI.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .schemas import CheckResult, FlaggedEmployer, MatchedPattern, ScamPattern

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FLAGGED_EMPLOYERS_PATH = DATA_DIR / "flagged_employers" / "flagged_employers.jsonl"
SCAM_PATTERNS_PATH = DATA_DIR / "scam_patterns" / "scam_patterns.jsonl"

SEVERITY_WEIGHT = {"high": 40, "medium": 20, "low": 10}
EMPLOYER_WEIGHT = 60

GENERAL_ADVICE = [
    "A legitimate employer never asks you to pay for a job, an interview, a training kit or a \u201cseat\u201d.",
    "Look up the company's phone number or email yourself, from a search engine or the institution's "
    "official site \u2014 never from the message you received.",
    "Check the sender's email domain character by character against the real one. Lookalike domains are "
    "the most common trick.",
    "Ask for the offer on letterhead with a named HR contact, and call the company's published "
    "switchboard to confirm that person exists.",
    "Never share bank details, OTPs, Aadhaar/PAN or your full date of birth to \u201cverify\u201d an "
    "internship offer.",
]

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"))
_PUNCT_FOLD = {
    ord("\u2018"): "'", ord("\u2019"): "'", ord("\u02bc"): "'",
    ord("\u201c"): '"', ord("\u201d"): '"',
}
for _cp in range(0x2010, 0x2016):
    _PUNCT_FOLD[_cp] = "-"


def normalize(text: str | None) -> str:
    """Lowercase, fold typographic characters, collapse whitespace."""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).lower()
    s = s.translate(_PUNCT_FOLD).translate(_ZERO_WIDTH)
    return re.sub(r"\s+", " ", s).strip()


def _hint_regex(hint: str) -> re.Pattern[str] | None:
    """Whitespace-tolerant, word-boundary-anchored matcher for one hint."""
    norm = normalize(hint)
    if not norm:
        return None
    body = r"\s+".join(re.escape(part) for part in norm.split(" "))
    prefix = r"\b" if re.match(r"[a-z0-9_]", norm) else ""
    suffix = r"\b" if re.search(r"[a-z0-9_]$", norm) else ""
    return re.compile(prefix + body + suffix)


def _contains_phrase(haystack_norm: str, phrase: str) -> bool:
    rx = _hint_regex(phrase)
    return bool(rx and rx.search(haystack_norm))


def _extract_host(query: str) -> str:
    """'Careers@Example-Corp.com/jobs' -> 'example-corp.com'"""
    q = normalize(query)
    if not q:
        return ""
    q = re.sub(r"^[a-z]+://", "", q)
    if "@" in q:
        q = q.rsplit("@", 1)[1]
    q = re.split(r"[/?\s]", q)[0]
    return re.sub(r"^www\.", "", q).rstrip(".")


def _domain_matches_query(domain: str, query: str) -> bool:
    d = re.sub(r"^www\.", "", normalize(domain))
    if not d:
        return False
    host = _extract_host(query)
    q = normalize(query)
    if host == d:
        return True
    if host and host.endswith("." + d):
        return True
    if len(q) >= 4 and q in d:
        return True
    if len(d) >= 4 and d in q:
        return True
    return False


def _name_matches_query(name: str, query: str) -> bool:
    n = normalize(name)
    q = normalize(query)
    if not n or len(q) < 3:
        return False
    if n == q:
        return True
    if q in n:
        return True
    if len(n) >= 4 and n in q:
        return True
    return False


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name} line {lineno} is not valid JSON: {exc}") from exc
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
        """Look up by company name, alias, domain, URL or email address.

        Queries shorter than 3 characters return nothing — otherwise a single
        letter would match most of the register.
        """
        if len(normalize(query)) < 3:
            return []
        matches = [
            emp
            for emp in self.flagged_employers
            if any(_name_matches_query(n, query) for n in [emp.company_name, *emp.aliases])
            or any(_domain_matches_query(d, query) for d in emp.domains)
        ]
        return sorted(matches, key=lambda e: e.id)

    def pattern_by_id(self, pattern_id: str) -> ScamPattern | None:
        for p in self.scam_patterns:
            if p.id == pattern_id:
                return p
        return None

    def employer_by_id(self, employer_id: str) -> FlaggedEmployer | None:
        for e in self.flagged_employers:
            if e.id == employer_id:
                return e
        return None

    def _employers_mentioned_in(self, text_norm: str) -> list[FlaggedEmployer]:
        found = []
        for emp in self.flagged_employers:
            names = [n for n in [emp.company_name, *emp.aliases] if len(normalize(n)) >= 5]
            if any(_contains_phrase(text_norm, n) for n in names) or any(
                _contains_phrase(text_norm, d) for d in emp.domains
            ):
                found.append(emp)
        return sorted(found, key=lambda e: e.id)

    def check_text(self, text: str) -> CheckResult:
        text_norm = normalize(text)
        matched: list[MatchedPattern] = []
        for pattern in self.scam_patterns:
            hits = [h for h in pattern.detection_hints if _contains_phrase(text_norm, h)]
            if hits:
                matched.append(MatchedPattern(pattern=pattern, matched_hints=hits))
        matched.sort(key=lambda m: m.pattern.id)

        matched_employers = self._employers_mentioned_in(text_norm)

        high_severity_hits = sum(1 for m in matched if m.pattern.severity == "high")
        # A high-severity marker corroborated by any second pattern is treated as
        # high: in practice a single high-severity hit is rarely an accident, and
        # a second marker alongside it almost never is. A lone high-severity hit
        # stays at medium so that one unlucky phrase cannot brand a real employer.
        corroborated = high_severity_hits >= 1 and len(matched) >= 2
        if matched_employers or high_severity_hits >= 2 or corroborated:
            confidence = "high"
        elif high_severity_hits == 1 or len(matched) >= 2:
            confidence = "medium"
        elif matched:
            confidence = "low"
        else:
            confidence = "none"

        score = sum(SEVERITY_WEIGHT.get(m.pattern.severity, 0) for m in matched)
        if matched_employers:
            score += EMPLOYER_WEIGHT
        score = min(100, score)

        if confidence == "none":
            explanation = (
                "No known scam patterns or flagged employers matched this text. "
                "This is not a guarantee the offer is legitimate — it only means "
                "nothing in the current dataset matched. Always verify independently."
            )
        else:
            names = ", ".join(m.pattern.name for m in matched) or "none"
            explanation = f"Matched pattern(s): {names}."
            if matched_employers:
                emp_names = ", ".join(e.company_name for e in matched_employers)
                explanation += f" Matched flagged record(s): {emp_names}."

        return CheckResult(
            matched_patterns=matched,
            matched_employers=matched_employers,
            confidence=confidence,
            score=score,
            explanation=explanation,
            advice=list(GENERAL_ADVICE),
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
