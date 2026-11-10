import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("fulltext", ROOT / "code/literature/fulltext.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def project(tmp_path):
    for rel in ("literature/fulltext.csv", "literature/extraction.csv", "inputs/attachments.csv"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    pd.DataFrame([
        {"record_id": "R1", "title": "Open paper", "doi": "10.1000/open", "duplicate_of": ""},
        {"record_id": "R2", "title": "Paywalled paper", "doi": "10.1000/paywall", "duplicate_of": ""},
        {"record_id": "R3", "title": "Excluded paper", "doi": "10.1000/out", "duplicate_of": ""},
    ]).to_csv(tmp_path / "literature/records.csv", index=False)
    rows = []
    for rid, a, b in (("R1", "INCLUDE", "INCLUDE"), ("R2", "MAYBE", "INCLUDE"), ("R3", "EXCLUDE", "EXCLUDE")):
        rows += [{"record_id": rid, "stage": "TITLE_ABSTRACT", "reviewer": "Screener A", "decision": a,
                  "exclusion_reason": "OUT_OF_SCOPE" if a == "EXCLUDE" else ""},
                 {"record_id": rid, "stage": "TITLE_ABSTRACT", "reviewer": "Screener B", "decision": b,
                  "exclusion_reason": "OUT_OF_SCOPE" if b == "EXCLUDE" else ""}]
    pd.DataFrame(rows).to_csv(tmp_path / "literature/screening_decisions.csv", index=False)
    return tmp_path


def ledger(root):
    return {r["record_id"]: r for r in MODULE.read_csv(root / "literature/fulltext.csv")}


def fake_fetch(url):
    if "openalex" in url and url.endswith("10.1000/open"):
        return 200, "application/json", json.dumps({"locations": [
            {"is_oa": True, "pdf_url": "https://repo.example.org/blocked.pdf"},
            {"is_oa": True, "pdf_url": "https://repo.example.org/open.pdf"}]}).encode()
    if "openalex" in url:
        return 200, "application/json", json.dumps({"locations": []}).encode()
    if url.endswith("blocked.pdf"):
        raise OSError("Tunnel connection failed: 403 Forbidden")
    return 200, "application/pdf", b"%PDF-1.4 fake"


def args(root, **kw):
    return type("A", (), {"root": str(root), **kw})()


def test_queue_takes_advanced_records_and_explicit_critical(tmp_path):
    root = project(tmp_path)
    MODULE.main(["queue", "--root", str(root)])
    assert set(ledger(root)) == {"R1", "R2"}
    MODULE.main(["queue", "--root", str(root), "--record-ids", "R2"])
    assert ledger(root)["R2"]["priority"] == "CRITICAL"


def test_open_access_fetch_and_manual_list(tmp_path, capsys):
    root = project(tmp_path)
    MODULE.main(["queue", "--root", str(root)])
    MODULE.cmd_fetch_oa(args(root), fetch=fake_fetch)
    rows = ledger(root)
    assert rows["R1"]["status"] == "AVAILABLE" and rows["R1"]["stored_path"].startswith("literature/fulltext/")
    assert "network policy" in rows["R1"]["attempts"]
    assert "repo.example.org" in capsys.readouterr().out
    assert rows["R2"]["status"] == "NEEDED" and "no open-access copy" in rows["R2"]["attempts"]
    MODULE.main(["manual-list", "--root", str(root)])
    assert ledger(root)["R2"]["status"] == "MANUAL_REQUESTED"
    assert "https://doi.org/10.1000/paywall" in (root / "results/fulltext/manual_download.md").read_text()


def test_finalize_requires_attempts_and_critical_needs_human_decision(tmp_path):
    root = project(tmp_path)
    MODULE.main(["queue", "--root", str(root), "--record-ids", "R2"])
    try:
        MODULE.main(["finalize", "--root", str(root), "--record-id", "R2", "--status", "ABSTRACT_ONLY", "--note", "x"])
        raise AssertionError("finalize must require attempts")
    except SystemExit as exc:
        assert "open-access attempt" in str(exc)
    MODULE.cmd_fetch_oa(args(root), fetch=fake_fetch)
    MODULE.main(["manual-list", "--root", str(root)])
    MODULE.main(["finalize", "--root", str(root), "--record-id", "R2", "--status", "ABSTRACT_ONLY",
                 "--note", "library copy unavailable"])
    issues = MODULE.audit_fulltext(root, strict=False, verify_files=False)
    assert any("CRITICAL paper not read" in i for i in issues)


def test_use_limits_on_screening_and_extraction(tmp_path):
    root = project(tmp_path)
    MODULE.main(["queue", "--root", str(root)])
    decisions = pd.read_csv(root / "literature/screening_decisions.csv", dtype=str).fillna("")
    decisions.loc[len(decisions)] = {"record_id": "R2", "stage": "FULL_TEXT", "reviewer": "Screener A",
                                     "decision": "EXCLUDE", "exclusion_reason": "NO_FULL_TEXT"}
    decisions.loc[len(decisions)] = {"record_id": "R1", "stage": "FULL_TEXT", "reviewer": "Screener A",
                                     "decision": "INCLUDE", "exclusion_reason": ""}
    decisions.to_csv(root / "literature/screening_decisions.csv", index=False)
    pd.DataFrame([{"record_id": "R1", "evidence_label": "DIRECT_EVIDENCE"}]).to_csv(
        root / "literature/extraction.csv", index=False)
    issues = MODULE.audit_fulltext(root, strict=False, verify_files=False)
    assert any("R2: excluded as NO_FULL_TEXT" in i for i in issues)
    assert any("R1: full-text decision" in i for i in issues)
    assert any("R1: extracted without a READ full text" in i for i in issues)


def test_mark_read_needs_obtained_text(tmp_path):
    root = project(tmp_path)
    MODULE.main(["queue", "--root", str(root)])
    try:
        MODULE.main(["mark-read", "--root", str(root), "--record-id", "R2", "--location", "p.1", "--role", "QA"])
        raise AssertionError("cannot read what was not obtained")
    except SystemExit as exc:
        assert "no obtained full text" in str(exc)
    MODULE.cmd_fetch_oa(args(root), fetch=fake_fetch)
    MODULE.main(["mark-read", "--root", str(root), "--record-id", "R1", "--location", "Sec. 3, Table 2",
                 "--role", "Quality Appraiser"])
    assert ledger(root)["R1"]["status"] == "READ"


def test_import_matches_user_pdfs_by_doi(tmp_path):
    root = project(tmp_path)
    MODULE.main(["queue", "--root", str(root)])
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "10.1000_paywall.pdf").write_bytes(b"%PDF-1.4 user copy")
    (downloads / "random.pdf").write_bytes(b"%PDF-1.4 unknown")
    MODULE.main(["import", "--root", str(root), "--dir", str(downloads)])
    row = ledger(root)["R2"]
    assert row["status"] == "AVAILABLE" and row["source"].startswith("USER_PROVIDED ATT-")
    assert row["stored_path"].startswith("inputs/raw/")
