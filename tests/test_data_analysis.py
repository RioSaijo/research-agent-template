import importlib.util
import json
import subprocess
import sys
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


ACQ = load("acquire", "code/data/acquire.py")
QUAL = load("quality", "code/data/quality.py")
STATS = load("stats", "code/analysis/stats.py")
REC = load("record_run", "code/analysis/record_run.py")

DATASET = {
    "data_id": "DATA-01",
    "format": {"timestamp_column": "ts", "timezone": "Asia/Tokyo", "expected_interval": "1h"},
    "variables": [
        {"name": "temp", "dtype": "float", "unit": "degC", "min": -10, "max": 50, "max_flatline": 5},
        {"name": "power", "dtype": "float", "unit": "kW", "min": 0, "max": 500},
    ],
}


def clean_frame(n=48):
    ts = pd.date_range("2026-01-01", periods=n, freq="h")
    rng = np.random.default_rng(1)
    return pd.DataFrame({"ts": ts.astype(str), "temp": 20 + rng.normal(0, 1, n), "power": 100 + rng.normal(0, 5, n)})


# --- data quality ---------------------------------------------------------

def test_clean_series_passes_quality():
    report = QUAL.profile_frame(clean_frame(), DATASET)
    assert report["status"] == "PASS", report["findings"]


def test_quality_detects_gap_duplicate_range_flatline_and_missing_unit():
    frame = clean_frame()
    frame = frame.drop(index=range(10, 15))
    frame.loc[20, "ts"] = frame.loc[19, "ts"]
    frame.loc[30, "power"] = -20
    frame.loc[35:44, "temp"] = 21.0
    dataset = json.loads(json.dumps(DATASET))
    dataset["variables"][1]["unit"] = ""
    checks = {f["check"] for f in QUAL.profile_frame(frame, dataset)["findings"]}
    assert {"gaps", "duplicate_timestamp", "range", "flatline", "unit"} <= checks


def test_quality_requires_timezone():
    dataset = dict(DATASET, format={"timestamp_column": "ts", "timezone": "", "expected_interval": "1h"})
    report = QUAL.profile_frame(clean_frame(), dataset)
    assert report["status"] == "FAIL"
    assert any(f["check"] == "timezone" for f in report["findings"])


# --- acquisition ----------------------------------------------------------

def test_register_is_immutable_and_verify_detects_modification(tmp_path):
    manifest = {"schema_version": "1.0.0", "datasets": [{"data_id": "DATA-01", "acquisition": {}, "files": []}]}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    source = tmp_path / "export.csv"
    source.write_text("ts,temp\n")
    common = ["--manifest", str(manifest_path), "--root", str(tmp_path)]
    assert ACQ.main(["register", *common, "--data-id", "DATA-01", "--path", str(source), "--method", "BMS_EXPORT"]) == 0
    raw = tmp_path / "data/raw/DATA-01/export.csv"
    assert raw.exists()
    assert ACQ.validate_manifest(json.loads(manifest_path.read_text()), tmp_path, strict=False) == []
    source.write_text("ts,temp\nchanged\n")
    try:
        ACQ.main(["register", *common, "--data-id", "DATA-01", "--path", str(source)])
        raise AssertionError("overwrite of raw data must be refused")
    except SystemExit as exc:
        assert "immutable" in str(exc)
    raw.chmod(0o644)
    raw.write_text("tampered")
    issues = ACQ.validate_manifest(json.loads(manifest_path.read_text()), tmp_path, strict=False)
    assert any("hash mismatch" in i for i in issues)


def test_non_redistributable_file_outside_raw_is_flagged():
    manifest = {"schema_version": "1.0.0", "datasets": [{
        "data_id": "D", "access": "CONFIDENTIAL", "redistributable": False,
        "files": [{"path": "results/leak.csv", "sha256": ""}]}]}
    issues = ACQ.validate_manifest(manifest, None, strict=False)
    assert any("outside gitignored" in i for i in issues)


def test_template_manifest_is_structurally_valid():
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    assert ACQ.validate_manifest(manifest, None, strict=False) == []
    assert ACQ.validate_manifest(manifest, None, strict=True)


# --- statistics -----------------------------------------------------------

def test_ashrae_style_metrics():
    y = np.array([10.0, 12.0, 14.0, 16.0])
    yhat = np.array([11.0, 11.0, 15.0, 15.0])
    assert STATS.rmse(y, yhat) == 1.0
    assert abs(STATS.cv_rmse(y, yhat) - 1.0 / 13.0) < 1e-12
    assert abs(STATS.cv_rmse(y, yhat, n_parameters=1) - np.sqrt(4 / 3) / 13.0) < 1e-12
    assert STATS.nmbe(y, yhat) == 0.0


def test_bootstrap_is_seeded_and_brackets_estimate():
    rng = np.random.default_rng(0)
    y = rng.normal(100, 10, 200)
    yhat = y + rng.normal(0, 3, 200)
    a = STATS.bootstrap_ci(STATS.rmse, y, yhat, n_boot=300, seed=7, block_length=24)
    b = STATS.bootstrap_ci(STATS.rmse, y, yhat, n_boot=300, seed=7, block_length=24)
    assert a == b
    assert a["ci_low"] <= a["estimate"] <= a["ci_high"]


def test_diebold_mariano_detects_better_model():
    rng = np.random.default_rng(3)
    good, bad = rng.normal(0, 1, 500), rng.normal(0, 2, 500)
    result = STATS.diebold_mariano(good, bad)
    assert result["statistic"] < 0 and result["p_value"] < 0.001


def test_multiplicity_adjustments():
    p = [0.01, 0.04, 0.03, 0.005]
    assert np.allclose(STATS.holm(p), [0.03, 0.06, 0.06, 0.02])
    assert np.allclose(STATS.benjamini_hochberg(p), [0.02, 0.04, 0.04, 0.02])


def test_cliffs_delta_and_effect_size():
    assert STATS.cliffs_delta([3, 4, 5], [1, 2]) == 1.0
    assert STATS.cliffs_delta([1, 2], [1, 2]) == 0.0


def test_rolling_origin_has_gap_and_no_leakage():
    folds = list(STATS.rolling_origin_splits(100, initial=50, horizon=10, gap=2))
    assert len(folds) == 4
    for train, test in folds:
        assert test[0] - train[-1] == 3
        assert STATS.temporal_leakage_issues(list(train), list(test), min_gap=2) == []
    assert STATS.temporal_leakage_issues([1, 2, 3], [3, 4])


def test_evaluate_with_baseline():
    rng = np.random.default_rng(5)
    y = 100 + rng.normal(0, 10, 300)
    model = y + rng.normal(0, 2, 300)
    base = y + rng.normal(0, 8, 300)
    result = STATS.evaluate(y, model, base, n_boot=200, seed=1, block_length=24)
    assert result["comparison"]["rmse_skill_score"]["estimate"] > 0.5
    assert result["comparison"]["squared_error_difference"]["ci_high"] < 0


# --- run recording --------------------------------------------------------

def _repo(tmp_path, status="LOCKED"):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/analysis_plan.json").write_text(json.dumps(
        {"status": status, "analyses": [{"analysis_id": "AN-01"}]}))
    (tmp_path / "in.csv").write_text("a\n1\n")
    (tmp_path / "make.py").write_text("import os, pathlib; pathlib.Path('out.txt').write_text(os.environ['RESEARCH_SEED'])\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "init"],
                   cwd=tmp_path, check=True)


def _args(tmp_path, run_type="PRIMARY"):
    return ["--root", str(tmp_path), "--run-id", "RUN-01", "--analysis-id", "AN-01", "--run-type", run_type,
            "--role", "Analyst", "--seed", "42", "--inputs", "in.csv", "--outputs", "out.txt",
            "--", sys.executable, "make.py"]


def test_record_run_writes_provenance(tmp_path):
    _repo(tmp_path)
    assert REC.main(_args(tmp_path)) == 0
    rows = pd.read_csv(tmp_path / "evidence/runs.csv", dtype=str)
    row = rows.iloc[0]
    assert row["run_type"] == "PRIMARY" and len(row["git_commit"]) == 40
    assert (tmp_path / "out.txt").read_text() == "42"
    assert (tmp_path / "results/environments/RUN-01.txt").exists()
    assert REC.main(_args(tmp_path)) == 2  # duplicate run_id refused


def test_record_run_refuses_confirmatory_run_without_locked_plan(tmp_path):
    _repo(tmp_path, status="DRAFT")
    assert REC.main(_args(tmp_path)) == 2
    assert REC.main(_args(tmp_path, run_type="EXPLORATORY")) == 0


def test_record_run_refuses_uncommitted_code(tmp_path):
    _repo(tmp_path)
    (tmp_path / "make.py").write_text("print('changed')\n")
    assert REC.main(_args(tmp_path)) == 2
