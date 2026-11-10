"""Gate 3 (Evidence and Verification) audit for machine-readable evidence artifacts.

Artifacts (all under ``evidence/``):

- ``analysis_plan.json``: pre-registered analyses, criteria, required checks, and
  required verification independence. Locked before any confirmatory run.
- ``runs.csv``: every analysis execution with commit, command, seed, and
  input/output SHA-256 hashes.
- ``checks.csv``: data-quality, alternative-explanation, sensitivity,
  falsification, reproduction, and independent-verification checks.
- ``claims.csv``: claim registry mirrored by the Claim Evidence Table in STATUS.md.

The audit enforces rules that a checklist cannot: criteria fixed before results,
automatic criterion evaluation, check coverage by claim type, role separation for
challenge and verification, independence levels, stale-artifact detection, and
retention of negative or unreported planned analyses.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PLACEHOLDER = "TO_DEFINE"

CLAIM_TYPES = {
    "DESCRIPTIVE", "ASSOCIATIONAL", "CAUSAL", "PREDICTIVE", "COMPARATIVE",
    "GENERALIZATION", "FEASIBILITY",
}
EVIDENCE_TYPES = {
    "LITERATURE", "STANDARD", "MEASUREMENT", "BMS_DATA", "EXPERIMENT", "SIMULATION",
    "ANALYTICAL", "STATISTICAL", "BENCHMARK", "SOFTWARE_TEST", "CASE_STUDY",
    "USER_EVALUATION",
}
VERIFICATION = {"NOT_VERIFIED", "INTERNALLY_VERIFIED", "INDEPENDENTLY_VERIFIED"}
CLAIM_STATUS = {"OPEN", "PRELIMINARY", "SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"}
CRITERION_MET = {"YES", "NO", "PARTIAL", "NOT_APPLIED"}
OPERATORS = {">=", ">", "<=", "<", "==", "BETWEEN", "MANUAL"}
RUN_TYPES = {"PRIMARY", "REPRODUCTION", "VERIFICATION", "SENSITIVITY", "EXPLORATORY"}
CHECK_TYPES = {
    "DATA_QUALITY", "LEAKAGE", "BASELINE", "ABLATION", "ALTERNATIVE_EXPLANATION",
    "SENSITIVITY", "ROBUSTNESS", "FALSIFICATION", "NEGATIVE_CONTROL", "TRANSFER",
    "REPRODUCTION", "INDEPENDENT_VERIFICATION", "GENERATED_DATA_VALIDATION",
}
GENERATED_CLASSES = {"SIMULATED", "SYNTHETIC", "AUGMENTED"}
# Claims resting only on generated data may be SUPPORTED only as statements about a model or method.
MODEL_EVIDENCE_TYPES = {"SIMULATION", "ANALYTICAL", "SOFTWARE_TEST", "BENCHMARK"}
GENERATED_CANNOT_SUPPORT = {"CAUSAL", "GENERALIZATION"}


def data_origin(manifest: dict, data_ids) -> str:
    """OBSERVED, GENERATED, MIXED, or UNKNOWN for the datasets an analysis uses."""
    by_id = {d.get("data_id"): d for d in manifest.get("datasets", [])}
    classes = {by_id.get(i, {}).get("provenance_class", "") for i in data_ids}
    if not classes or classes & {"", "TO_DEFINE"}:
        return "UNKNOWN"
    generated = classes & GENERATED_CLASSES
    if not generated:
        return "OBSERVED"
    return "GENERATED" if classes <= {"SIMULATED", "SYNTHETIC"} else "MIXED"
CHECK_RESULTS = {"PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"}

# Independence levels, weakest to strongest. RERUN is reproducibility, not independence.
INDEPENDENCE_LEVELS = [
    "NONE", "RERUN", "ALTERNATIVE_METHOD", "INDEPENDENT_IMPLEMENTATION",
    "INDEPENDENT_DATA", "EXTERNAL",
]
INTERNAL_LEVELS = {"RERUN", "ALTERNATIVE_METHOD"}
INDEPENDENT_LEVELS = {"INDEPENDENT_IMPLEMENTATION", "INDEPENDENT_DATA", "EXTERNAL"}

# Checks that must be performed by a role different from the primary analyst.
ROLE_SEPARATED_CHECKS = {
    "ALTERNATIVE_EXPLANATION", "FALSIFICATION", "NEGATIVE_CONTROL", "INDEPENDENT_VERIFICATION",
}


def minimum_required_checks(claim_type: str, central: bool) -> set[str]:
    """Checks that cannot be removed from the plan, whatever the plan says."""
    required = {"DATA_QUALITY"}
    if central:
        required |= {"ALTERNATIVE_EXPLANATION", "SENSITIVITY"}
    if claim_type == "CAUSAL":
        required |= {"ALTERNATIVE_EXPLANATION", "FALSIFICATION"}
    if claim_type == "PREDICTIVE":
        required |= {"LEAKAGE", "BASELINE"}
    if claim_type == "COMPARATIVE":
        required |= {"BASELINE"}
    if claim_type == "GENERALIZATION":
        required |= {"TRANSFER"}
    return required


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def parse_time(value: str) -> datetime | None:
    if not value or value == PLACEHOLDER:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def is_defined(value: object) -> bool:
    return value not in (None, "", PLACEHOLDER, [])


def evaluate_criterion(criterion: dict, observed: str) -> str | None:
    """Return YES/NO for numeric criteria, or None when it must be judged manually."""
    operator = criterion.get("operator", "")
    if operator in ("MANUAL", PLACEHOLDER, ""):
        return None
    try:
        value = float(observed)
    except ValueError:
        return None
    threshold = criterion.get("threshold")
    if operator == "BETWEEN":
        low, high = (float(x) for x in threshold)
        return "YES" if low <= value <= high else "NO"
    threshold = float(threshold)
    result = {
        ">=": value >= threshold, ">": value > threshold, "<=": value <= threshold,
        "<": value < threshold, "==": value == threshold,
    }[operator]
    return "YES" if result else "NO"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_plan(plan: dict, strict: bool) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    if plan.get("schema_version") != "1.0.0":
        issues.append(("PLAN", "unsupported analysis_plan schema_version"))
    if strict:
        if plan.get("status") != "LOCKED":
            issues.append(("PLAN", "analysis plan is not LOCKED"))
        if parse_time(plan.get("locked_at", "")) is None:
            issues.append(("PLAN", "analysis plan locked_at is missing or not ISO 8601"))
    seen_claims: set[str] = set()
    for analysis in plan.get("analyses", []):
        aid = analysis.get("analysis_id", "UNKNOWN")
        claim_type = analysis.get("claim_type", PLACEHOLDER)
        if is_defined(claim_type) and claim_type not in CLAIM_TYPES:
            issues.append((aid, f"invalid claim_type: {claim_type}"))
        criterion = analysis.get("criterion", {})
        operator = criterion.get("operator", PLACEHOLDER)
        if is_defined(operator):
            if operator not in OPERATORS:
                issues.append((aid, f"invalid criterion operator: {operator}"))
            elif operator == "BETWEEN" and not (
                isinstance(criterion.get("threshold"), list) and len(criterion["threshold"]) == 2
            ):
                issues.append((aid, "BETWEEN criterion needs a [low, high] threshold"))
            elif operator not in ("BETWEEN", "MANUAL") and not isinstance(
                criterion.get("threshold"), (int, float)
            ):
                issues.append((aid, "numeric criterion needs a numeric threshold"))
            elif operator == "MANUAL" and not is_defined(criterion.get("description")):
                issues.append((aid, "MANUAL criterion needs a pre-registered description"))
        for check in analysis.get("required_checks", []):
            if check not in CHECK_TYPES:
                issues.append((aid, f"invalid required check: {check}"))
        level = analysis.get("verification", {}).get("independence_level", PLACEHOLDER)
        if is_defined(level) and level not in INDEPENDENCE_LEVELS:
            issues.append((aid, f"invalid independence_level: {level}"))
        for claim_id in analysis.get("claim_ids", []):
            if claim_id in seen_claims:
                issues.append((aid, f"claim pre-registered in more than one analysis: {claim_id}"))
            seen_claims.add(claim_id)
        if strict:
            for field in ("rq_id", "claim_type", "hypothesis", "metric", "baseline",
                          "expected_direction", "uncertainty_method"):
                if not is_defined(analysis.get(field)):
                    issues.append((aid, f"plan field undefined: {field}"))
            if not is_defined(operator):
                issues.append((aid, "plan criterion undefined"))
            if not is_defined(level):
                issues.append((aid, "plan verification independence_level undefined"))
            if not analysis.get("claim_ids"):
                issues.append((aid, "analysis pre-registers no claim"))
    return issues


def audit_evidence(
    plan: dict,
    runs: list[dict[str, str]],
    checks: list[dict[str, str]],
    claims: list[dict[str, str]],
    strict: bool = True,
    root: Path | None = None,
    status_claims: dict[str, dict[str, str]] | None = None,
    manifest: dict | None = None,
) -> list[tuple[str, str]]:
    """Return (scope, message) issues. ``root`` enables artifact existence and hash checks."""
    issues = audit_plan(plan, strict)
    analyses = {a.get("analysis_id", ""): a for a in plan.get("analyses", [])}
    locked_at = parse_time(plan.get("locked_at", ""))
    run_by_id = {r.get("run_id", ""): r for r in runs}

    for run in runs:
        rid = run.get("run_id", "UNKNOWN")
        if run.get("analysis_id") not in analyses:
            issues.append((rid, f"run references unknown analysis: {run.get('analysis_id')}"))
        run_type = run.get("run_type", "")
        if run_type not in RUN_TYPES:
            issues.append((rid, f"invalid run_type: {run_type}"))
        confirmatory = run_type in RUN_TYPES - {"EXPLORATORY"}
        run_at = parse_time(run.get("run_at", ""))
        if confirmatory:
            if run_at is None:
                issues.append((rid, "confirmatory run has no valid run_at"))
            elif locked_at is not None and run_at < locked_at:
                issues.append((rid, "confirmatory run precedes analysis plan lock"))
            elif locked_at is None and strict:
                issues.append((rid, "confirmatory run exists but analysis plan was never locked"))
            for field in ("git_commit", "command", "role"):
                if not run.get(field):
                    issues.append((rid, f"confirmatory run missing {field}"))
        if any(p.startswith("data/generated/") for p in split_list(run.get("inputs", ""))) and \
                run.get("input_data_origin") not in {"GENERATED", "MIXED"}:
            issues.append((rid, "run reads data/generated/ but input_data_origin is not GENERATED or MIXED"))
        for kind in ("inputs", "outputs"):
            paths = split_list(run.get(kind, ""))
            hashes = split_list(run.get(f"{kind[:-1]}_sha256", ""))
            if len(paths) != len(hashes):
                issues.append((rid, f"{kind} and {kind[:-1]}_sha256 counts differ"))
                continue
            if confirmatory and kind == "outputs" and not paths:
                issues.append((rid, "confirmatory run records no outputs"))
            if root is None:
                continue
            for rel, expected in zip(paths, hashes):
                target = root / rel
                if not target.exists():
                    issues.append((rid, f"recorded {kind[:-1]} missing: {rel}"))
                elif sha256_file(target) != expected.lower():
                    issues.append((rid, f"stale or modified {kind[:-1]} (hash mismatch): {rel}"))

    checks_by_claim: dict[str, list[dict[str, str]]] = defaultdict(list)
    check_by_id = {c.get("check_id", ""): c for c in checks}
    for check in checks:
        cid = check.get("check_id", "UNKNOWN")
        if check.get("check_type") not in CHECK_TYPES:
            issues.append((cid, f"invalid check_type: {check.get('check_type')}"))
        if check.get("result") not in CHECK_RESULTS:
            issues.append((cid, f"invalid check result: {check.get('result')}"))
        if check.get("result") in {"FAIL", "INCONCLUSIVE"} and not check.get("impact_on_claim"):
            issues.append((cid, "FAIL/INCONCLUSIVE check has no impact_on_claim"))
        level = check.get("independence_level", "")
        if level and level not in INDEPENDENCE_LEVELS:
            issues.append((cid, f"invalid independence_level: {level}"))
        if check.get("run_id") and check["run_id"] not in run_by_id:
            issues.append((cid, f"check references unknown run: {check['run_id']}"))
        if root is not None and check.get("artifact") and not (root / check["artifact"]).exists():
            issues.append((cid, f"check artifact missing: {check['artifact']}"))
        if check.get("claim_id"):
            checks_by_claim[check["claim_id"]].append(check)

    reported: set[str] = set()
    for claim in claims:
        clid = claim.get("claim_id", "UNKNOWN")
        reported.add(clid)
        analysis = analyses.get(claim.get("analysis_id", ""))
        status = claim.get("claim_status", "")
        verification = claim.get("verification", "")
        met = claim.get("criterion_met", "")
        for field, allowed in (("evidence_type", EVIDENCE_TYPES), ("verification", VERIFICATION),
                               ("claim_status", CLAIM_STATUS), ("criterion_met", CRITERION_MET)):
            if claim.get(field) not in allowed:
                issues.append((clid, f"invalid {field}: {claim.get(field)}"))
        if analysis is None:
            issues.append((clid, f"claim references unknown analysis: {claim.get('analysis_id')}"))
            continue
        pre_registered = clid in analysis.get("claim_ids", [])
        positive = status in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
        if not pre_registered and status not in {"OPEN", "PRELIMINARY", "UNSUPPORTED"}:
            issues.append((clid, "claim was not pre-registered; post-hoc claims stay PRELIMINARY"))

        primary = run_by_id.get(claim.get("primary_run_id", ""))
        if status != "OPEN":
            if primary is None:
                issues.append((clid, "claim has no recorded primary run"))
            elif primary.get("run_type") != "PRIMARY":
                issues.append((clid, "primary_run_id is not a PRIMARY run"))
            elif primary.get("analysis_id") != claim.get("analysis_id"):
                issues.append((clid, "primary run belongs to a different analysis"))

        computed = evaluate_criterion(analysis.get("criterion", {}), claim.get("observed_value", ""))
        if computed is not None and met in {"YES", "NO"} and computed != met:
            issues.append((clid, f"criterion_met={met} contradicts pre-registered criterion (computed {computed})"))
        if analysis.get("criterion", {}).get("operator") == "MANUAL" and met in {"YES", "PARTIAL"}:
            judged = [c for c in checks_by_claim[clid] if c.get("check_type") == "INDEPENDENT_VERIFICATION"
                      and c.get("result") == "PASS"]
            if not judged:
                issues.append((clid, "MANUAL criterion judged met without a passing independent check"))
        if status == "SUPPORTED" and met != "YES":
            issues.append((clid, "SUPPORTED requires criterion_met=YES"))
        if status == "PARTIALLY_SUPPORTED":
            if met not in {"YES", "PARTIAL"}:
                issues.append((clid, "PARTIALLY_SUPPORTED requires criterion_met YES or PARTIAL"))
            if not claim.get("limitation"):
                issues.append((clid, "PARTIALLY_SUPPORTED requires a stated limitation"))
        if positive and not claim.get("uncertainty"):
            issues.append((clid, "supported claim reports no uncertainty"))

        claim_checks = checks_by_claim[clid]
        analyst = primary.get("role", "") if primary else ""
        required = set(analysis.get("required_checks", [])) | minimum_required_checks(
            analysis.get("claim_type", ""), bool(analysis.get("central"))
        )
        if positive:
            passed = {c.get("check_type") for c in claim_checks if c.get("result") == "PASS"}
            for check_type in sorted(required - passed):
                issues.append((clid, f"required check not passed: {check_type}"))
            if status == "SUPPORTED" and any(c.get("result") == "FAIL" for c in claim_checks):
                issues.append((clid, "SUPPORTED claim has a FAIL check"))
        for check in claim_checks:
            if check.get("check_type") in ROLE_SEPARATED_CHECKS and analyst and check.get("role") == analyst:
                issues.append((clid, f"{check.get('check_type')} done by the primary analyst role ({analyst})"))

        vcheck = check_by_id.get(claim.get("verification_check_id", ""))
        if verification != "NOT_VERIFIED":
            if vcheck is None:
                issues.append((clid, f"{verification} without a verification_check_id"))
            else:
                level = vcheck.get("independence_level", "")
                if vcheck.get("result") != "PASS":
                    issues.append((clid, "verification check did not PASS"))
                if vcheck.get("claim_id") != clid:
                    issues.append((clid, "verification check belongs to another claim"))
                if verification == "INDEPENDENTLY_VERIFIED":
                    if level not in INDEPENDENT_LEVELS:
                        issues.append((clid, f"INDEPENDENTLY_VERIFIED needs an independent level, got {level or 'NONE'}"))
                    if analyst and vcheck.get("role") == analyst:
                        issues.append((clid, "independent verification performed by the primary analyst role"))
                elif level not in INTERNAL_LEVELS | INDEPENDENT_LEVELS:
                    issues.append((clid, f"INTERNALLY_VERIFIED needs RERUN or stronger, got {level or 'NONE'}"))
        planned_level = analysis.get("verification", {}).get("independence_level", "")
        if status == "SUPPORTED" and planned_level in INDEPENDENT_LEVELS and verification != "INDEPENDENTLY_VERIFIED":
            issues.append((clid, f"plan requires {planned_level} verification before SUPPORTED"))

        if manifest is not None:
            used = analysis.get("data_ids", [])
            origin = data_origin(manifest, used)
            by_id = {d.get("data_id"): d for d in manifest.get("datasets", [])}
            generated_ids = [d for d in used if by_id.get(d, {}).get("provenance_class") in GENERATED_CLASSES]
            if generated_ids:
                if not claim.get("generated_data_disclosure"):
                    issues.append((clid, f"uses generated data ({', '.join(generated_ids)}) without generated_data_disclosure"))
                if positive:
                    for did in generated_ids:
                        validated = any(c.get("check_type") == "GENERATED_DATA_VALIDATION" and c.get("data_id") == did
                                        and c.get("result") == "PASS" for c in checks)
                        if not validated or by_id[did].get("generation", {}).get("validation_status") != "PASS":
                            issues.append((clid, f"generated dataset {did} has no passing GENERATED_DATA_VALIDATION"))
                for did in generated_ids:
                    gen = by_id[did].get("generation", {})
                    if gen.get("within_reference_conditions") is False and status == "SUPPORTED":
                        issues.append((clid, f"{did} represents conditions outside its reference data; "
                                             "claims using it cannot be SUPPORTED"))
                    shared = set(gen.get("calibration_data_ids", [])) & set(used)
                    if shared:
                        leakage_ok = any(c.get("check_type") == "LEAKAGE" and c.get("result") == "PASS"
                                         for c in claim_checks)
                        if not leakage_ok:
                            issues.append((clid, f"{did} was generated from {', '.join(sorted(shared))}, which the same "
                                                 "analysis also uses; a passing LEAKAGE check is required"))
                if origin == "GENERATED" and status == "SUPPORTED":
                    if claim.get("evidence_type") not in MODEL_EVIDENCE_TYPES:
                        issues.append((clid, "claim rests only on generated data; SUPPORTED needs evidence_type "
                                             "SIMULATION/ANALYTICAL/SOFTWARE_TEST/BENCHMARK (a statement about the model)"))
                    if analysis.get("claim_type") in GENERATED_CANNOT_SUPPORT:
                        issues.append((clid, f"{analysis.get('claim_type')} claim cannot be SUPPORTED by generated data alone"))
            if status_claims is not None and clid in status_claims and origin in {"GENERATED", "MIXED"}:
                if status_claims[clid].get("data_origin") != origin:
                    issues.append((clid, f"STATUS.md Data Origin must show {origin}"))
        if status_claims is not None:
            mirror = status_claims.get(clid)
            if mirror is None:
                issues.append((clid, "claim missing from STATUS.md Claim Evidence Table"))
            else:
                for field in ("claim_status", "verification"):
                    if mirror.get(field) != claim.get(field):
                        issues.append((clid, f"STATUS.md {field} differs: {mirror.get(field)} vs {claim.get(field)}"))

    if strict:
        for aid, analysis in analyses.items():
            if not any(r.get("analysis_id") == aid and r.get("run_type") == "PRIMARY" for r in runs):
                issues.append((aid, "planned analysis has no PRIMARY run (unreported analysis)"))
            for clid in analysis.get("claim_ids", []):
                if clid not in reported:
                    issues.append((aid, f"pre-registered claim not reported (negative results must be kept): {clid}"))
        for claim in claims:
            if claim.get("claim_status") == "OPEN":
                issues.append((claim.get("claim_id", "UNKNOWN"), "claim still OPEN at Gate 3"))
    return issues


def parse_status_claims(path: Path) -> dict[str, dict[str, str]]:
    """Read the Claim Evidence Table from STATUS.md, skipping placeholder rows."""
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## Claim Evidence Table")
    except ValueError:
        return {}
    header: list[str] = []
    result: dict[str, dict[str, str]] = {}
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not header:
            header = cells
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        row = dict(zip(header, cells))
        if row.get("Claim", "") in ("", "要検討", PLACEHOLDER):
            continue
        result[row.get("Claim ID", "")] = {
            "claim_status": row.get("Claim Status", ""),
            "verification": row.get("Verification", ""),
            "data_origin": row.get("Data Origin", ""),
        }
    return result


def gate3_report(claims: list[dict[str, str]], issues: list[tuple[str, str]]) -> dict:
    by_scope: dict[str, list[str]] = defaultdict(list)
    for scope, message in issues:
        by_scope[scope].append(message)
    claim_ids = {c.get("claim_id", "") for c in claims}
    per_claim = {
        c.get("claim_id", ""): {
            "claim_status": c.get("claim_status", ""),
            "verification": c.get("verification", ""),
            "gate3": "PASS" if not by_scope.get(c.get("claim_id", "")) else "FAIL",
            "issues": by_scope.get(c.get("claim_id", ""), []),
        }
        for c in claims
    }
    other = {scope: msgs for scope, msgs in by_scope.items() if scope not in claim_ids}
    return {
        "gate3": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "claims": per_claim,
        "plan_run_check_issues": other,
    }


def load_all(args: argparse.Namespace):
    base = Path(args.evidence_dir)
    plan = json.loads((base / "analysis_plan.json").read_text(encoding="utf-8"))
    return (plan, read_csv(base / "runs.csv"), read_csv(base / "checks.csv"), read_csv(base / "claims.csv"))


def run_audit(args: argparse.Namespace):
    plan, runs, checks, claims = load_all(args)
    root = Path(args.root) if args.verify_files else None
    status_claims = parse_status_claims(Path(args.status)) if args.status else None
    manifest_path = Path(args.root) / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    issues = audit_evidence(plan, runs, checks, claims, strict=not args.allow_incomplete,
                            root=root, status_claims=status_claims, manifest=manifest)
    return claims, issues


def cmd_audit(args: argparse.Namespace) -> int:
    _, issues = run_audit(args)
    for scope, message in issues:
        print(f"[evidence-audit] {scope}: {message}")
    return 1 if issues else 0


def cmd_report(args: argparse.Namespace) -> int:
    claims, issues = run_audit(args)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(gate3_report(claims, issues), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    return 1 if issues else 0


def cmd_hash(args: argparse.Namespace) -> int:
    """Print 'path;...' and 'sha256;...' strings for a runs.csv row."""
    paths = list(args.paths)
    print(";".join(paths))
    print(";".join(sha256_file(Path(args.root) / p) for p in paths))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("audit", cmd_audit), ("report", cmd_report)):
        p = sub.add_parser(name)
        p.add_argument("--evidence-dir", default="evidence")
        p.add_argument("--status", help="STATUS.md path for Claim Evidence Table consistency")
        p.add_argument("--root", default=".", help="repository root for artifact paths")
        p.add_argument("--verify-files", action="store_true", help="check artifact existence and SHA-256")
        p.add_argument("--allow-incomplete", action="store_true")
        if name == "report":
            p.add_argument("--output", default="results/evidence/gate3_report.json")
        p.set_defaults(func=func)
    h = sub.add_parser("hash")
    h.add_argument("paths", nargs="+")
    h.add_argument("--root", default=".")
    h.set_defaults(func=cmd_hash)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
