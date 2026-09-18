from api.classifier import Dataset

KNOWN_SCAM_TEXT = """
Congratulations! You have been selected for our Summer Internship Program,
in association with IIT, only 3 seats left — offer closes in 24 hours.
To confirm your seat, please pay a refundable registration fee of Rs. 499
via the UPI QR code below and fill out this form with your register number.
"""

KNOWN_LEGIT_TEXT = """
Thank you for applying to the Software Engineering Internship at Acme Corp.
We would like to invite you for a technical interview on Monday at 10am via
our official careers portal. No payment is required at any stage of our
recruitment process. Please confirm your availability by replying to this
email from careers@acme-corp.com.
"""


def test_known_scam_text_flags_high_confidence():
    ds = Dataset.load()
    result = ds.check_text(KNOWN_SCAM_TEXT)
    matched_names = {m.pattern.name for m in result.matched_patterns}

    assert result.confidence in {"medium", "high"}
    assert "Upfront fee via personal UPI/QR code" in matched_names
    assert "Artificial urgency and limited-seats pressure" in matched_names
    # every matched pattern must carry at least one source (transparency requirement)
    for m in result.matched_patterns:
        assert len(m.pattern.sources) >= 1


def test_known_legit_text_does_not_flag():
    ds = Dataset.load()
    result = ds.check_text(KNOWN_LEGIT_TEXT)

    assert result.confidence == "none"
    assert result.matched_patterns == []
    assert result.matched_employers == []


def test_lookup_finds_seeded_flagged_employer():
    ds = Dataset.load()
    matches = ds.find_employers("Launched Global")

    assert len(matches) == 1
    assert matches[0].status == "confirmed"
    assert len(matches[0].sources) >= 1


def test_lookup_no_match_for_unknown_company():
    ds = Dataset.load()
    matches = ds.find_employers("Some Totally Unremarkable Real Company Pvt Ltd")

    assert matches == []


def test_every_dataset_record_has_a_source():
    """Guards CLAUDE.md rule 1: never add a record without a citable source."""
    ds = Dataset.load()
    for emp in ds.flagged_employers:
        assert len(emp.sources) >= 1, f"{emp.id} has no source"
    for pattern in ds.scam_patterns:
        assert len(pattern.sources) >= 1, f"{pattern.id} has no source"
