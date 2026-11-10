import copy
import importlib.util
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("intake", ROOT / "code/intake/intake.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

INTAKE = json.loads((ROOT / "inputs/intake.json").read_text(encoding="utf-8"))


def project(tmp_path, **intake_over):
    for rel in ("inputs/attachments.csv", "literature/records.csv", "literature/search_log.csv",
                "data/manifest.json", "data/source_search_log.csv", "data/candidates.csv"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes((ROOT / rel).read_bytes())
    intake = copy.deepcopy(INTAKE)
    intake.update(intake_over)
    (tmp_path / "inputs/intake.json").write_text(json.dumps(intake, ensure_ascii=False))
    return tmp_path


def register(root, path, kind="auto", purpose="user says this is the closest prior study"):
    return MODULE.main(["register", "--root", str(root), "--path", str(path), "--kind", kind, "--purpose", purpose])


def test_template_intake_is_valid_but_incomplete():
    assert MODULE.audit_intake(ROOT, strict=False, verify_files=False) == []
    assert MODULE.audit_intake(ROOT, strict=True, verify_files=False)


def test_stage_determines_route():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        issues = MODULE.audit_intake(project(Path(d), stage="S0", route="SYSTEMATIC_REVIEW"), False, False)
    assert any("requires route EXPLORATION" in i for i in issues)


def test_exploration_needs_options_and_human_selection(tmp_path):
    exploration = {"status": "OPTIONS_PRESENTED", "options": [{"option_id": "O1", "problem": "p"}],
                   "selected_option": "", "human_approval": ""}
    root = project(tmp_path, stage="S0", route="EXPLORATION", stage_rationale="interest only",
                   brief={"aim": "use BEMS data"}, exploration=exploration)
    issues = MODULE.audit_intake(root, strict=True, verify_files=False)
    assert any("missing candidate_rq" in i for i in issues)
    assert any("at least two options" in i for i in issues)
    assert any("Gate 1 cannot start" in i for i in issues)
    exploration = {"status": "SELECTED", "selected_option": "O2", "human_approval": "",
                   "options": [{"option_id": "O1"}, {"option_id": "O2"}]}
    root = project(tmp_path, stage="S0", route="EXPLORATION", exploration=exploration)
    assert any("human approval" in i for i in MODULE.audit_intake(root, strict=False, verify_files=False))


def test_register_hashes_stores_read_only_and_dedupes(tmp_path):
    root = project(tmp_path)
    pdf = tmp_path / "closest.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    assert register(root, pdf) == 0
    rows = pd.read_csv(root / "inputs/attachments.csv", dtype=str)
    row = rows.iloc[0]
    assert row["attachment_id"] == "ATT-001" and row["kind"] == "UNCLASSIFIED"
    assert row["stored_path"] == "inputs/raw/ATT-001/closest.pdf"
    assert (root / row["stored_path"]).exists()
    assert register(root, pdf) == 0
    assert len(pd.read_csv(root / "inputs/attachments.csv")) == 1
    issues = MODULE.audit_intake(root, strict=True, verify_files=True)
    assert any("not classified" in i for i in issues)


def test_paper_routes_to_literature_as_other_methods(tmp_path):
    root = project(tmp_path)
    pdf = tmp_path / "closest.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    register(root, pdf)
    assert MODULE.main(["route", "--root", str(root), "--id", "ATT-001", "--kind", "paper",
                        "--title", "Closest study", "--doi", "10.1234/abc", "--year", "2024"]) == 0
    records = pd.read_csv(root / "literature/records.csv", dtype=str)
    assert records.iloc[0]["record_id"] == "ATT-001"
    assert records.iloc[0]["source_database"] == "USER_PROVIDED"
    log = pd.read_csv(root / "literature/search_log.csv", dtype=str)
    assert log.iloc[0]["search_id"] == "ATT-001"
    assert MODULE.audit_intake(root, strict=False, verify_files=True) == []


def test_bibliography_bibtex_and_ris(tmp_path):
    root = project(tmp_path)
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{a,\n  title = {First study},\n  year = {2021},\n  doi = {10.1/x},\n}\n"
                   "@article{b,\n  title = {Second study},\n  year = {2022},\n}\n")
    register(root, bib, purpose="papers my supervisor recommended")
    MODULE.main(["route", "--root", str(root), "--id", "ATT-001"])
    titles = list(pd.read_csv(root / "literature/records.csv")["title"])
    assert titles == ["First study", "Second study"]
    assert MODULE.parse_ris("TY  - JOUR\nTI  - Ris study\nPY  - 2020/01/01\nDO  - 10.2/y\nER  - \n") == [
        {"title": "Ris study", "year": "2020", "doi": "10.2/y"}]


def test_dataset_enters_data_chain_as_candidate(tmp_path):
    root = project(tmp_path)
    csv_file = tmp_path / "bms.csv"
    csv_file.write_text("ts,power\n2026-01-01 00:00,10\n")
    register(root, csv_file, purpose="BMS export from our building")
    assert MODULE.main(["route", "--root", str(root), "--id", "ATT-001", "--data-id", "DATA-07",
                        "--requirement-ids", "DR-01"]) == 0
    manifest = json.loads((root / "data/manifest.json").read_text())
    item = next(d for d in manifest["datasets"] if d["data_id"] == "DATA-07")
    assert item["provenance_class"] == "OBSERVED" and item["files"][0]["path"].startswith("data/raw/DATA-07/")
    cand = pd.read_csv(root / "data/candidates.csv", dtype=str).iloc[-1]
    assert cand["decision"] == "PENDING" and cand["data_id"] == "DATA-07"


def test_documents_wait_for_a_role_and_can_be_marked(tmp_path):
    root = project(tmp_path)
    doc = tmp_path / "reviews.txt"
    doc.write_text("Reviewer 1: the baseline is weak.")
    register(root, doc, kind="review_comments", purpose="journal reviewer comments")
    MODULE.main(["route", "--root", str(root), "--id", "ATT-001"])
    assert any("waiting for a role" in i for i in MODULE.audit_intake(root, strict=True, verify_files=False))
    MODULE.main(["mark", "--root", str(root), "--id", "ATT-001", "--status", "ROUTED", "--routed-ids", "RF-EXT-01"])
    row = pd.read_csv(root / "inputs/attachments.csv", dtype=str).iloc[0]
    assert row["status"] == "ROUTED" and row["routed_ids"] == "RF-EXT-01"


def test_tampered_attachment_is_detected(tmp_path):
    root = project(tmp_path)
    doc = tmp_path / "notes.txt"
    doc.write_text("idea")
    register(root, doc, kind="notes", purpose="brainstorm notes")
    stored = root / "inputs/raw/ATT-001/notes.txt"
    stored.chmod(0o644)
    stored.write_text("changed")
    assert any("hash mismatch" in i for i in MODULE.audit_intake(root, strict=False, verify_files=True))


def test_dataset_replaces_template_entry_but_not_registered_data(tmp_path):
    root = project(tmp_path)
    csv_file = tmp_path / "bms.csv"
    csv_file.write_text("ts,power\n2026-01-01 00:00,10\n")
    register(root, csv_file, purpose="BMS export")
    assert MODULE.main(["route", "--root", str(root), "--id", "ATT-001", "--data-id", "DATA-01"]) == 0
    manifest = json.loads((root / "data/manifest.json").read_text())
    items = [d for d in manifest["datasets"] if d["data_id"] == "DATA-01"]
    assert len(items) == 1 and items[0]["access"] == "INTERNAL" and items[0]["files"]
    other = tmp_path / "bms2.csv"
    other.write_text("ts,power\n2026-02-01 00:00,11\n")
    register(root, other, purpose="another export")
    try:
        MODULE.main(["route", "--root", str(root), "--id", "ATT-002", "--data-id", "DATA-01"])
        raise AssertionError("registered data must not be overwritten")
    except SystemExit as exc:
        assert "choose a new --data-id" in str(exc)


def test_mark_does_not_duplicate_notes(tmp_path):
    root = project(tmp_path)
    doc = tmp_path / "notes.txt"
    doc.write_text("idea")
    register(root, doc, kind="notes", purpose="memo")
    for _ in range(2):
        MODULE.main(["mark", "--root", str(root), "--id", "ATT-001", "--status", "ROUTED",
                     "--routed-ids", "intake.json#brief", "--note", "moved to brief"])
    notes = pd.read_csv(root / "inputs/attachments.csv", dtype=str).iloc[0]["notes"]
    assert notes.count("moved to brief") == 1
