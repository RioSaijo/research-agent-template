import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "code" / "literature" / "systematic_review.py"
SPEC = importlib.util.spec_from_file_location("systematic_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_deduplication_prefers_doi_then_title_year():
    rows = [
        {"record_id": "R1", "title": "Building Energy Prediction", "year": "2024", "doi": "https://doi.org/10.1/ABC"},
        {"record_id": "R2", "title": "Different title", "year": "2024", "doi": "doi:10.1/abc"},
        {"record_id": "R3", "title": "Building-energy prediction!", "year": "2024", "doi": ""},
    ]
    result = MODULE.mark_duplicates(rows)
    assert result[1]["duplicate_of"] == "R1"
    assert result[2]["duplicate_of"] == "R1"


def test_audit_requires_two_screeners_and_exclusion_reason():
    records = [{"record_id": "R1", "duplicate_of": ""}]
    decisions = [{
        "record_id": "R1", "stage": "TITLE_ABSTRACT", "reviewer": "A",
        "decision": "EXCLUDE", "exclusion_reason": "",
    }]
    issues = MODULE.audit_screening(records, decisions)
    assert any("dual title/abstract" in issue for issue in issues)
    assert any("exclusion reason" in issue for issue in issues)


def test_audit_detects_unresolved_conflict():
    records = [{"record_id": "R1", "duplicate_of": ""}]
    decisions = [
        {"record_id": "R1", "stage": "TITLE_ABSTRACT", "reviewer": "A", "decision": "INCLUDE", "exclusion_reason": ""},
        {"record_id": "R1", "stage": "TITLE_ABSTRACT", "reviewer": "B", "decision": "EXCLUDE", "exclusion_reason": "OUT_OF_SCOPE"},
    ]
    issues = MODULE.audit_screening(records, decisions)
    assert any("unresolved screening conflict" in issue for issue in issues)


def test_prisma_counts_preserve_retrievals_and_duplicates():
    records = [
        {"record_id": "R1", "duplicate_of": ""},
        {"record_id": "R2", "duplicate_of": "R1"},
        {"record_id": "R3", "duplicate_of": ""},
    ]
    decisions = [
        {"record_id": "R1", "stage": "TITLE_ABSTRACT", "decision": "INCLUDE"},
        {"record_id": "R3", "stage": "TITLE_ABSTRACT", "decision": "EXCLUDE"},
        {"record_id": "R1", "stage": "FULL_TEXT", "decision": "INCLUDE"},
    ]
    counts = MODULE.prisma_counts(records, decisions)
    assert counts == {
        "records_identified": 3,
        "duplicates_removed": 1,
        "unique_records": 2,
        "title_abstract_screened": 2,
        "title_abstract_excluded": 1,
        "full_text_assessed": 1,
        "full_text_excluded": 0,
        "studies_included": 1,
    }
