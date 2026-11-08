import copy
import hashlib
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "code" / "evidence" / "evidence_audit.py"
SPEC = importlib.util.spec_from_file_location("evidence_audit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


PLAN = {
    "schema_version": "1.0.0",
    "status": "LOCKED",
    "locked_at": "2026-01-01T00:00:00Z",
    "analyses": [{
        "analysis_id": "AN-01", "rq_id": "RQ-01", "claim_ids": ["CL-01"], "central": True,
        "claim_type": "PREDICTIVE", "hypothesis": "h", "metric": "CV(RMSE)",
        "criterion": {"operator": "<=", "threshold": 0.3, "description": "ASHRAE G14 hourly"},
        "baseline": "persistence", "expected_direction": "lower", "uncertainty_method": "bootstrap CI",
        "required_checks": ["DATA_QUALITY"],
        "verification": {"method": "second implementation", "independence_level": "INDEPENDENT_IMPLEMENTATION"},
    }],
}
RUNS = [
    {"run_id": "RUN-01", "analysis_id": "AN-01", "run_type": "PRIMARY", "role": "Analyst",
     "run_at": "2026-01-02T00:00:00Z", "git_commit": "abc", "command": "python a.py",
     "inputs": "", "input_sha256": "", "outputs": "results/m.json", "output_sha256": "00"},
]
CHECKS = [
    {"check_id": f"CK-{t}", "claim_id": "CL-01", "check_type": t, "role": "Methods Challenger",
     "result": "PASS", "independence_level": ""}
    for t in ("DATA_QUALITY", "ALTERNATIVE_EXPLANATION", "SENSITIVITY", "LEAKAGE", "BASELINE")
] + [{"check_id": "CK-IV", "claim_id": "CL-01", "check_type": "INDEPENDENT_VERIFICATION",
      "role": "Verifier", "result": "PASS", "independence_level": "INDEPENDENT_IMPLEMENTATION"}]
CLAIM = {
    "claim_id": "CL-01", "rq_id": "RQ-01", "analysis_id": "AN-01", "claim": "c",
    "evidence_type": "STATISTICAL", "primary_run_id": "RUN-01", "observed_value": "0.21",
    "uncertainty": "95% CI 0.18-0.24", "criterion_met": "YES",
    "verification": "INDEPENDENTLY_VERIFIED", "verification_check_id": "CK-IV",
    "claim_status": "SUPPORTED", "limitation": "",
}


def audit(plan=PLAN, runs=RUNS, checks=CHECKS, claims=None, **kwargs):
    return [m for _, m in MODULE.audit_evidence(plan, runs, checks, claims or [CLAIM], **kwargs)]


def test_complete_supported_claim_passes():
    assert audit() == []


def test_criterion_is_evaluated_against_preregistered_threshold():
    claim = dict(CLAIM, observed_value="0.45")
    assert any("contradicts pre-registered criterion" in m for m in audit(claims=[claim]))


def test_supported_requires_criterion_met():
    claim = dict(CLAIM, criterion_met="NO", observed_value="0.45")
    assert any("SUPPORTED requires criterion_met=YES" in m for m in audit(claims=[claim]))


def test_confirmatory_run_before_lock_is_flagged():
    runs = [dict(RUNS[0], run_at="2025-12-31T00:00:00Z")]
    assert any("precedes analysis plan lock" in m for m in audit(runs=runs))


def test_claim_type_minimum_checks_cannot_be_removed_from_plan():
    checks = [c for c in CHECKS if c["check_type"] != "LEAKAGE"]
    assert any("required check not passed: LEAKAGE" in m for m in audit(checks=checks))


def test_rerun_is_not_independent_verification():
    checks = [dict(c, independence_level="RERUN") if c["check_id"] == "CK-IV" else c for c in CHECKS]
    assert any("needs an independent level" in m for m in audit(checks=checks))


def test_challenge_by_primary_analyst_is_flagged():
    checks = [dict(c, role="Analyst") if c["check_type"] == "ALTERNATIVE_EXPLANATION" else c for c in CHECKS]
    assert any("done by the primary analyst role" in m for m in audit(checks=checks))


def test_plan_required_independence_blocks_internal_support():
    claim = dict(CLAIM, verification="NOT_VERIFIED", verification_check_id="")
    assert any("plan requires INDEPENDENT_IMPLEMENTATION" in m for m in audit(claims=[claim]))


def test_post_hoc_claim_cannot_be_supported():
    plan = copy.deepcopy(PLAN)
    plan["analyses"][0]["claim_ids"] = ["CL-99"]
    issues = audit(plan=plan)
    assert any("not pre-registered" in m for m in issues)
    assert any("pre-registered claim not reported" in m for m in issues)


def test_unsupported_negative_result_is_valid():
    claim = dict(CLAIM, observed_value="0.45", criterion_met="NO", claim_status="UNSUPPORTED",
                 verification="NOT_VERIFIED", verification_check_id="")
    assert audit(claims=[claim]) == []


def test_stale_output_hash_is_detected(tmp_path):
    output = tmp_path / "results" / "m.json"
    output.parent.mkdir()
    output.write_text("{}", encoding="utf-8")
    good = hashlib.sha256(b"{}").hexdigest()
    runs = [dict(RUNS[0], output_sha256=good)]
    assert audit(runs=runs, root=tmp_path) == []
    output.write_text('{"changed": 1}', encoding="utf-8")
    assert any("hash mismatch" in m for m in audit(runs=runs, root=tmp_path))


def test_status_table_mismatch_is_detected(tmp_path):
    status = tmp_path / "STATUS.md"
    status.write_text(
        "## Claim Evidence Table\n\n"
        "| Claim ID | RQ | Claim | Evidence Type | Primary Evidence | Independent Check | Verification | Claim Status | Referee |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| CL-01 | RQ-01 | c | STATISTICAL | RUN-01 | CK-IV | INDEPENDENTLY_VERIFIED | PRELIMINARY | NOT_REVIEWED |\n"
        "\n## Next\n",
        encoding="utf-8",
    )
    mirror = MODULE.parse_status_claims(status)
    assert any("STATUS.md claim_status differs" in m for m in audit(status_claims=mirror))


def test_incomplete_mode_accepts_template_plan():
    plan = {"schema_version": "1.0.0", "status": "DRAFT", "locked_at": "TO_DEFINE", "analyses": [{
        "analysis_id": "AN-01", "claim_ids": ["CL-01"], "claim_type": "TO_DEFINE",
        "criterion": {"operator": "TO_DEFINE"}, "verification": {"independence_level": "TO_DEFINE"},
    }]}
    assert MODULE.audit_evidence(plan, [], [], [], strict=False) == []
    assert MODULE.audit_evidence(plan, [], [], [], strict=True)
