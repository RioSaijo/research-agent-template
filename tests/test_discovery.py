import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("discovery", ROOT / "code/data/discovery.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


GAP = {"gap_id": "GAP-01", "gap_type": "TRANSFER_GAP", "description": "d", "supporting_record_ids": "R1",
       "contradicting_record_ids": "", "search_ids": "S1", "evidence_quality": "MODERATE",
       "minimum_closing_design": "multi-climate validation", "analyst_role": "Gap Analyst",
       "challenger_role": "Gap Challenger", "challenger_decision": "ACCEPTED",
       "challenger_notes": "adjacent-field and synonym counter-search found no closing study"}
REQ = {"requirement_id": "DR-01", "rq_id": "RQ-01", "gap_id": "GAP-01", "analysis_id": "AN-01",
       "required_evidence": "hourly load in >=2 climates", "variables": "electricity_kW;outdoor_temp",
       "priority": "MUST", "derivation": "CV(RMSE) criterion per climate", "status": "SATISFIED",
       "satisfied_by": "DATA-01", "notes": ""}
SEARCHES = [
    {"search_id": "DS-01", "requirement_ids": "DR-01", "source": "datacite", "source_type": "DATA_REPOSITORY",
     "result_count": "40", "retrieved_count": "40", "notes": ""},
    {"search_id": "DS-02", "requirement_ids": "DR-01", "source": "included studies", "source_type": "LITERATURE_DATA",
     "result_count": "5", "retrieved_count": "5", "notes": ""},
]
CAND = {"candidate_id": "DC-01", "requirement_ids": "DR-01", "name": "x", "search_id": "DS-01",
        "literature_record_id": "", "license": "CC-BY-4.0", "access": "PUBLIC",
        **{s: "2" for s in MODULE.SCORES}, "decision": "SELECTED", "decision_reason": "best fit",
        "screener_role": "Data Screener", "data_id": "DATA-01"}


def chain(**over):
    base = {
        "rqs": {"RQ-01": ["GAP-01"]},
        "gaps": [GAP], "extraction": [{"record_id": "R1"}], "lit_searches": [{"search_id": "S1"}],
        "lit_records": [{"record_id": "R1"}], "requirements": [REQ], "searches": SEARCHES, "candidates": [CAND],
        "plan": {"analyses": [{"analysis_id": "AN-01", "rq_id": "RQ-01", "data_ids": ["DATA-01"]}]},
        "manifest": {"datasets": [{"data_id": "DATA-01", "related_rq": ["RQ-01"]}]},
        "root": ROOT,
    }
    base.update(over)
    return base


def messages(**over):
    return [m for _, m in MODULE.audit_chain(chain(**over))]


def test_complete_chain_passes():
    assert messages() == []


def test_gap_must_be_challenged_by_another_role():
    gap = dict(GAP, challenger_role="Gap Analyst")
    assert any("other than the Gap Analyst" in m for m in messages(gaps=[gap]))


def test_gap_cannot_rest_on_absence_of_hits():
    gap = dict(GAP, supporting_record_ids="")
    assert any("absence of hits is not a gap" in m for m in messages(gaps=[gap]))


def test_gap_studies_must_be_appraised():
    assert any("not quality-appraised" in m for m in messages(extraction=[]))


def test_rq_must_be_grounded_in_accepted_gap():
    gap = dict(GAP, challenger_decision="REJECTED")
    assert any("not grounded" in m for m in messages(gaps=[gap]))


def test_must_requirement_needs_repository_and_literature_data_search():
    issues = messages(searches=SEARCHES[:1])
    assert any("without a LITERATURE_DATA search" in m for m in issues)


def test_insufficient_requires_all_pathways():
    req = dict(REQ, status="INSUFFICIENT", satisfied_by="")
    issues = messages(requirements=[req])
    assert any("pathway SIMULATION" in m for m in issues)
    assert any("pathway PROXY" in m for m in issues)


def test_proxy_requires_validity_notes():
    req = dict(REQ, status="PROXY")
    assert any("proxy validity" in m for m in messages(requirements=[req]))


def test_unjustified_dataset_collection_is_flagged():
    manifest = {"datasets": [{"data_id": "DATA-01", "related_rq": ["RQ-01"]}, {"data_id": "DATA-99"}]}
    assert any("not justified by any data requirement" in m for m in messages(manifest=manifest))


def test_selected_candidate_needs_manifest_and_license():
    cand = dict(CAND, license="", data_id="")
    issues = messages(candidates=[cand])
    assert any("undefined license" in m for m in issues)
    assert any("no manifest dataset" in m for m in issues)


def test_result_cap_needs_justification():
    searches = [dict(SEARCHES[0], result_count="500", retrieved_count="100"), SEARCHES[1]]
    assert any("without justification" in m for m in messages(searches=searches))


def test_rq_table_parser(tmp_path):
    project = tmp_path / "PROJECT.md"
    project.write_text("## Research Questions\n\n| RQ ID | Research Question | Gap IDs | Type | Status |\n"
                       "|---|---|---|---|---|\n| RQ-01 | q | GAP-01; GAP-02 | Primary | DRAFT |\n"
                       "| RQ-02 | 要検討 | 要検討 | Secondary | DRAFT |\n\n## Next\n")
    assert MODULE.parse_rq_table(project) == {"RQ-01": ["GAP-01", "GAP-02"]}


def test_datacite_search_paginates_and_logs_pending_candidates(tmp_path):
    pages = {
        1: {"meta": {"total": 3}, "data": [{"attributes": {"doi": "10.1/a", "titles": [{"title": "A"}],
                                                           "publisher": "P", "rightsList": [{"rightsIdentifier": "cc-by-4.0"}],
                                                           "publicationYear": 2024}}] * 2},
        2: {"meta": {"total": 3}, "data": [{"attributes": {"doi": "10.1/b", "titles": [{"title": "B"}]}}]},
    }

    def fake_fetch(url):
        return pages[2 if "page%5Bnumber%5D=2" in url else 1]

    (tmp_path / "data").mkdir()
    args = MODULE.build_parser().parse_args(["search", "--source", "datacite", "--query", "building load",
                                             "--search-id", "DS-01", "--requirement-ids", "DR-01",
                                             "--root", str(tmp_path)])
    assert MODULE.run_search(args, fetch=fake_fetch) == 0
    cands = MODULE.read_csv(tmp_path / "data/candidates.csv")
    log = MODULE.read_csv(tmp_path / "data/source_search_log.csv")
    assert len(cands) == 3 and all(c["decision"] == "PENDING" for c in cands)
    assert log[0]["result_count"] == "3" and log[0]["retrieved_count"] == "3"
    assert cands[0]["doi_or_url"] == "https://doi.org/10.1/a"


def test_repository_templates_pass_incomplete_audit():
    assert MODULE.audit_chain(MODULE.load_chain(ROOT), strict=False) == []
    assert json.loads(json.dumps(MODULE.build_matrix(MODULE.load_chain(ROOT))))["rqs"] == {}
