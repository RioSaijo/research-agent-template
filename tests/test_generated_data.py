import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


GEN = load("generate", "code/data/generate.py")
DISC = load("discovery_g", "code/data/discovery.py")
EVID = load("evidence_g", "code/evidence/evidence_audit.py")
REC = load("record_run_g", "code/analysis/record_run.py")


def observed_series(n=24 * 21, seed=0):
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2026-01-01", periods=n, freq="h")
    power = 100 + 20 * np.sin(np.arange(n) * 2 * np.pi / 24) + rng.normal(0, 3, n)
    return pd.DataFrame({"ts": ts.astype(str), "power": power})


def project(tmp_path):
    (tmp_path / "data/raw/OBS-01").mkdir(parents=True)
    obs = tmp_path / "data/raw/OBS-01/load.csv"
    observed_series().to_csv(obs, index=False)
    manifest = {"schema_version": "1.0.0", "datasets": [
        {"data_id": "OBS-01", "provenance_class": "OBSERVED", "files": [{"path": "data/raw/OBS-01/load.csv"}],
         "format": {"timestamp_column": "ts", "timezone": "UTC", "expected_interval": "1h"}},
        {"data_id": "GEN-01", "generation": {"fidelity_criteria": [
            {"metric": "ks", "variable": "power", "max": 0.1},
            {"metric": "mean_rel_diff", "variable": "power", "max": 0.05},
            {"metric": "acf_lag1_diff", "variable": "power", "max": 0.1}]}},
    ]}
    (tmp_path / "data/manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/checks.csv").write_text(
        "check_id,claim_id,analysis_id,data_id,check_type,description,role,run_id,independence_level,artifact,result,impact_on_claim,checked_at\n")
    return tmp_path


def bootstrap(tmp_path, role="Data Generator"):
    return GEN.main(["bootstrap", "--root", str(tmp_path), "--manifest", str(tmp_path / "data/manifest.json"),
                     "--data-id", "GEN-01", "--reference-data-id", "OBS-01", "--n-rows", "336",
                     "--block-length", "24", "--seed", "7", "--purpose", "extend winter coverage",
                     "--reason-not-collected", "no public or BMS data for February; provider declined",
                     "--limitations", "inherits OBS-01 building and climate", "--role", role])


def test_bootstrap_labels_file_sidecar_and_manifest(tmp_path):
    root = project(tmp_path)
    assert bootstrap(root) == 0
    manifest = json.loads((root / "data/manifest.json").read_text())
    item = manifest["datasets"][1]
    assert item["provenance_class"] == "SYNTHETIC" and item["label"] == GEN.LABEL
    path = root / item["files"][0]["path"]
    assert item["files"][0]["path"].startswith("data/generated/GEN-01/")
    assert set(pd.read_csv(path)["data_origin"]) == {"SYNTHETIC"}
    sidecar = json.loads(path.with_name(path.name + ".provenance.json").read_text())
    assert sidecar["label"] == GEN.LABEL and sidecar["generation"]["calibration_data_ids"] == ["OBS-01"]
    assert GEN.validate_generated_entry(item, root, strict=True) == []
    try:
        bootstrap(root)
        raise AssertionError("generated files must be immutable")
    except SystemExit as exc:
        assert "immutable" in str(exc)


def test_validation_needs_separate_role_and_records_check(tmp_path):
    root = project(tmp_path)
    bootstrap(root)
    base = ["validate", "--root", str(root), "--manifest", str(root / "data/manifest.json"), "--data-id", "GEN-01",
            "--reference-data-id", "OBS-01", "--checks", str(root / "evidence/checks.csv"),
            "--output", str(root / "results/v.json")]
    try:
        GEN.main(base + ["--role", "Data Generator"])
        raise AssertionError("generator must not validate its own data")
    except SystemExit as exc:
        assert "other than the generator" in str(exc)
    assert GEN.main(base + ["--role", "Generated Data Validator", "--record-check", "CK-GV-01"]) == 0
    manifest = json.loads((root / "data/manifest.json").read_text())
    assert manifest["datasets"][1]["generation"]["validation_status"] == "PASS"
    check = pd.read_csv(root / "evidence/checks.csv").iloc[0]
    assert check["check_type"] == "GENERATED_DATA_VALIDATION" and check["result"] == "PASS"


def test_validation_fails_without_criteria_and_detects_copying():
    ref = observed_series()
    assert GEN.validate_frames(ref.copy(), ref, [])["status"] == "FAIL"
    report = GEN.validate_frames(ref.copy(), ref, [{"metric": "duplicate_rate", "max": 0.05}])
    assert report["duplicate_rate"] == 1.0 and report["status"] == "FAIL"


def test_manifest_rules_catch_unlabeled_generated_data(tmp_path):
    item = {"data_id": "G", "provenance_class": "SYNTHETIC", "files": [{"path": "data/raw/G/x.csv"}], "generation": {}}
    issues = GEN.validate_generated_entry(item, None, strict=False)
    assert any("must carry label" in i for i in issues)
    assert any("outside data/generated/" in i for i in issues)
    assert any("generation.reason_not_collected undefined" in i for i in issues)
    observed = {"data_id": "O", "provenance_class": "OBSERVED", "files": [{"path": "data/generated/O/x.csv"}]}
    assert any("has a file in data/generated/" in i for i in GEN.validate_generated_entry(observed, None, False))


def test_row_level_origin_is_enforced():
    frame = pd.DataFrame({"x": [1, 2], "data_origin": ["SYNTHETIC", "OBSERVED"]})
    assert GEN.check_origin_column(frame, "SYNTHETIC")
    assert GEN.check_origin_column(frame, "AUGMENTED") == []
    assert GEN.check_origin_column(frame.drop(columns="data_origin"), "SIMULATED") == ["missing data_origin column"]


# ---- discovery: GENERATED requirement status ---------------------------------------------

def disc_chain(status="GENERATED", validation="PASS", source_types=("DATA_REPOSITORY", "LITERATURE_DATA", "API",
                                                                    "BMS_BEMS_IOT", "EXTERNAL_PROVIDER")):
    searches = [{"search_id": f"S{i}", "requirement_ids": "DR-01", "source_type": t, "result_count": "0",
                 "retrieved_count": "0"} for i, t in enumerate(source_types)]
    return {"rqs": {}, "gaps": [], "extraction": [], "lit_searches": [], "lit_records": [], "rubric": {},
            "requirements": [{"requirement_id": "DR-01", "rq_id": "RQ-01", "priority": "MUST", "status": status,
                              "satisfied_by": "GEN-01", "notes": "no observed February data anywhere",
                              "required_evidence": "hourly winter load", "variables": "power_kW",
                              "derivation": "criterion needs February coverage"}],
            "searches": searches, "candidates": [], "plan": {},
            "manifest": {"datasets": [{"data_id": "GEN-01", "provenance_class": "SYNTHETIC", "related_rq": ["RQ-01"],
                                       "generation": {"validation_status": validation}}]},
            "root": ROOT}


def disc_messages(**kw):
    return [m for _, m in DISC.audit_chain(disc_chain(**kw), strict=True) if "justified" not in m]


def test_generated_requirement_passes_after_collection_attempts():
    assert disc_messages() == []


def test_generated_requires_collection_attempts_and_validation():
    issues = disc_messages(validation="NOT_VALIDATED", source_types=("DATA_REPOSITORY", "LITERATURE_DATA"))
    assert any("pathway API" in m for m in issues)
    assert any("pathway EXTERNAL_PROVIDER" in m for m in issues)
    assert any("not passed fidelity validation" in m for m in issues)


def test_generated_data_cannot_satisfy_requirement():
    assert any("use GENERATED" in m for m in disc_messages(status="SATISFIED"))


# ---- evidence: claims on generated data ---------------------------------------------------

PLAN = {"schema_version": "1.0.0", "status": "LOCKED", "locked_at": "2026-01-01T00:00:00Z", "analyses": [{
    "analysis_id": "AN-01", "rq_id": "RQ-01", "claim_ids": ["CL-01"], "central": False, "claim_type": "PREDICTIVE",
    "criterion": {"operator": "<=", "threshold": 0.3}, "required_checks": [], "data_ids": ["GEN-01"],
    "verification": {"independence_level": "NONE"}}]}
RUNS = [{"run_id": "R1", "analysis_id": "AN-01", "run_type": "PRIMARY", "role": "Analyst",
         "run_at": "2026-01-02T00:00:00Z", "git_commit": "abc", "command": "x",
         "inputs": "data/generated/GEN-01/bootstrap.csv", "input_sha256": "00", "outputs": "o", "output_sha256": "00",
         "input_data_origin": "GENERATED"}]
CHECKS = [{"check_id": f"C-{t}", "claim_id": "CL-01", "check_type": t, "role": "Methods Challenger", "result": "PASS"}
          for t in ("DATA_QUALITY", "LEAKAGE", "BASELINE")] + [
    {"check_id": "C-GV", "data_id": "GEN-01", "check_type": "GENERATED_DATA_VALIDATION", "role": "Generated Data Validator",
     "result": "PASS"}]
CLAIM = {"claim_id": "CL-01", "analysis_id": "AN-01", "evidence_type": "SIMULATION", "primary_run_id": "R1",
         "observed_value": "0.2", "uncertainty": "CI", "criterion_met": "YES", "verification": "NOT_VERIFIED",
         "claim_status": "SUPPORTED", "generated_data_disclosure": "model trained and tested on SYNTHETIC GEN-01"}
MANIFEST = {"datasets": [{"data_id": "GEN-01", "provenance_class": "SYNTHETIC",
                          "generation": {"validation_status": "PASS"}}]}


def evid(plan=PLAN, runs=RUNS, checks=CHECKS, claim=CLAIM, status=None):
    return [m for _, m in EVID.audit_evidence(plan, runs, checks, [claim], strict=False, manifest=MANIFEST,
                                              status_claims=status)]


def test_model_claim_on_validated_generated_data_passes():
    assert evid() == []


def test_generated_claim_needs_disclosure_and_validation():
    issues = evid(claim=dict(CLAIM, generated_data_disclosure=""), checks=CHECKS[:3])
    assert any("without generated_data_disclosure" in m for m in issues)
    assert any("no passing GENERATED_DATA_VALIDATION" in m for m in issues)


def test_generated_only_claim_cannot_be_empirical_or_causal():
    assert any("statement about the model" in m for m in evid(claim=dict(CLAIM, evidence_type="STATISTICAL")))
    plan = copy.deepcopy(PLAN)
    plan["analyses"][0]["claim_type"] = "GENERALIZATION"
    plan["analyses"][0]["required_checks"] = []
    issues = evid(plan=plan, checks=CHECKS + [{"check_id": "C-T", "claim_id": "CL-01", "check_type": "TRANSFER",
                                               "role": "Methods Challenger", "result": "PASS"}])
    assert any("cannot be SUPPORTED by generated data alone" in m for m in issues)


def test_status_table_and_runs_must_show_generated_origin():
    issues = evid(status={"CL-01": {"claim_status": "SUPPORTED", "verification": "NOT_VERIFIED", "data_origin": "OBSERVED"}})
    assert any("Data Origin must show GENERATED" in m for m in issues)
    assert any("input_data_origin" in m for m in evid(runs=[dict(RUNS[0], input_data_origin="")]))


def test_manuscript_disclosure(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "evidence").mkdir()
    (tmp_path / "paper").mkdir()
    (tmp_path / "data/manifest.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "evidence/analysis_plan.json").write_text(json.dumps(PLAN))
    pd.DataFrame([CLAIM]).to_csv(tmp_path / "evidence/claims.csv", index=False)
    body = tmp_path / "paper/body.tex"
    body.write_text("Results on synthetic data.")
    assert GEN.disclosure_issues(tmp_path, body)
    body.write_text("Results on \\GeneratedData{GEN-01} data.")
    assert GEN.disclosure_issues(tmp_path, body) == []


def test_record_run_labels_generated_inputs(tmp_path):
    assert REC.input_origin(tmp_path, ["data/generated/GEN-01/x.csv"]) == "GENERATED"
    (tmp_path / "data").mkdir()
    (tmp_path / "data/manifest.json").write_text(json.dumps({"datasets": [
        {"data_id": "OBS-01", "provenance_class": "OBSERVED", "files": [{"path": "data/raw/OBS-01/a.csv"}]},
        {"data_id": "GEN-01", "provenance_class": "SYNTHETIC", "files": [{"path": "data/generated/GEN-01/b.csv"}]}]}))
    assert REC.input_origin(tmp_path, ["data/raw/OBS-01/a.csv"]) == "OBSERVED"
    assert REC.input_origin(tmp_path, ["data/raw/OBS-01/a.csv", "data/generated/GEN-01/b.csv"]) == "MIXED"
