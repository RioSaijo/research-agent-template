"""Generated data (simulated, synthetic, augmented): registration, validation, and disclosure.

Generated data is a last resort when required data cannot be collected. It must be labeled
everywhere it travels, so it can never be mistaken for observed measurements:

1. ``data/manifest.json``: ``provenance_class`` and the fixed ``label`` text, plus a
   ``generation`` block (method, generator, parameters, seed, calibration data, purpose,
   why the data could not be collected, pre-registered fidelity criteria, limitations).
2. The file itself: stored under ``data/generated/<ID>/`` with a ``data_origin`` column on
   every row, and a ``<file>.provenance.json`` sidecar carrying the same label.
3. ``evidence/runs.csv``: ``input_data_origin`` is set automatically by record_run.py.
4. ``evidence/claims.csv`` and the STATUS.md Claim Evidence Table: a disclosure and a
   Data Origin column for claims that use generated data.
5. The manuscript: every generated dataset used by a claim appears as ``\\GeneratedData{ID}``.

Commands:
  register          label and register a generated CSV produced by any generator
  bootstrap         built-in generator: moving-block bootstrap of an observed series
  validate          compare generated data with reference data against fidelity criteria
  check-disclosure  verify the manuscript discloses every generated dataset used by a claim
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROVENANCE_CLASSES = {"OBSERVED", "DERIVED", "SIMULATED", "SYNTHETIC", "AUGMENTED"}
GENERATED_CLASSES = {"SIMULATED", "SYNTHETIC", "AUGMENTED"}
ROW_ORIGINS = {"OBSERVED", "DERIVED", "SIMULATED", "SYNTHETIC"}
METHODS = {"SIMULATION", "BOOTSTRAP", "STATISTICAL_MODEL", "ML_MODEL", "RULE_BASED", "LLM", "OTHER"}
FIDELITY_METRICS = {"ks", "mean_rel_diff", "std_rel_diff", "acf_lag1_diff", "range_coverage", "duplicate_rate"}
ORIGIN_COLUMN = "data_origin"
GENERATED_PREFIX = "data/generated/"
LABEL = "GENERATED DATA - not observed measurements"
REQUIRED_GENERATION_FIELDS = ("method", "generator", "seed", "purpose", "reason_not_collected", "target_conditions",
                              "within_reference_conditions", "fidelity_criteria", "limitations", "generated_by")
# Resampling methods can only recombine observed rows; they cannot create conditions absent from the reference.
RESAMPLING_METHODS = {"BOOTSTRAP"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dataset(manifest: dict, data_id: str) -> dict:
    for item in manifest.get("datasets", []):
        if item.get("data_id") == data_id:
            return item
    raise SystemExit(f"[generate] unknown data_id {data_id}; add an entry to data/manifest.json first")


def is_generated(item: dict) -> bool:
    return item.get("provenance_class") in GENERATED_CLASSES


def dataset_origin(manifest: dict, data_ids: Iterable[str]) -> str:
    """OBSERVED, GENERATED, MIXED, or UNKNOWN for a set of data IDs."""
    by_id = {d.get("data_id"): d for d in manifest.get("datasets", [])}
    classes = {by_id[i].get("provenance_class", "") for i in data_ids if i in by_id}
    if not classes or "" in classes:
        return "UNKNOWN"
    generated = classes & GENERATED_CLASSES
    if not generated:
        return "OBSERVED"
    if classes - GENERATED_CLASSES or "AUGMENTED" in classes:
        return "MIXED"
    return "GENERATED"


def path_origin(manifest: dict, paths: Iterable[str]) -> str:
    """Origin of input files, resolved through manifest file entries and the generated folder."""
    owners = []
    for rel in paths:
        owner = next((d.get("data_id") for d in manifest.get("datasets", [])
                      if any(f.get("path") == rel for f in d.get("files", []))), None)
        if owner:
            owners.append(owner)
        elif rel.startswith(GENERATED_PREFIX):
            return "MIXED" if owners else "GENERATED"
    return dataset_origin(manifest, owners) if owners else "NOT_REGISTERED"


def check_origin_column(frame: pd.DataFrame, provenance_class: str) -> list[str]:
    if ORIGIN_COLUMN not in frame.columns:
        return [f"missing {ORIGIN_COLUMN} column"]
    values = set(frame[ORIGIN_COLUMN].astype(str))
    issues = [f"invalid {ORIGIN_COLUMN} value: {v}" for v in sorted(values - ROW_ORIGINS)]
    if provenance_class in {"SIMULATED", "SYNTHETIC"} and values != {provenance_class}:
        issues.append(f"every row must have {ORIGIN_COLUMN}={provenance_class}; found {sorted(values)}")
    if provenance_class == "AUGMENTED" and not (values & {"SIMULATED", "SYNTHETIC"} and values & {"OBSERVED", "DERIVED"}):
        issues.append(f"AUGMENTED data must label both observed and generated rows; found {sorted(values)}")
    return issues


def validate_generated_entry(item: dict, root: Path | None, strict: bool) -> list[str]:
    """Manifest-level rules for one dataset; used by acquire.py verify."""
    did = item.get("data_id", "UNKNOWN")
    pclass = item.get("provenance_class", "")
    pclass = "" if pclass == "TO_DEFINE" else pclass
    issues: list[str] = []
    if pclass and pclass not in PROVENANCE_CLASSES:
        return [f"{did}: invalid provenance_class {pclass}"]
    if strict and not pclass:
        issues.append(f"{did}: provenance_class undefined")
    files = [f for f in item.get("files", []) if f.get("path")]
    if pclass in GENERATED_CLASSES:
        if item.get("label") != LABEL:
            issues.append(f"{did}: generated dataset must carry label '{LABEL}'")
        gen = item.get("generation", {})
        if gen.get("method") and gen["method"] not in METHODS:
            issues.append(f"{did}: invalid generation method {gen['method']}")
        for field in REQUIRED_GENERATION_FIELDS:
            if gen.get(field) in (None, "", [], "TO_DEFINE"):
                issues.append(f"{did}: generation.{field} undefined")
        for crit in gen.get("fidelity_criteria", []):
            if crit.get("metric") not in FIDELITY_METRICS:
                issues.append(f"{did}: invalid fidelity metric {crit.get('metric')}")
        for f in files:
            if not f["path"].startswith(GENERATED_PREFIX):
                issues.append(f"{did}: generated file outside {GENERATED_PREFIX}: {f['path']}")
            if root is None:
                continue
            target = root / f["path"]
            if not target.exists():
                continue
            sidecar = target.with_name(target.name + ".provenance.json")
            if not sidecar.exists():
                issues.append(f"{did}: missing provenance sidecar for {f['path']}")
            elif json.loads(sidecar.read_text(encoding="utf-8")).get("label") != LABEL:
                issues.append(f"{did}: sidecar label missing or altered for {f['path']}")
            if target.suffix == ".csv":
                issues += [f"{did}: {f['path']}: {m}" for m in check_origin_column(pd.read_csv(target), pclass)]
    else:
        for f in files:
            if f["path"].startswith(GENERATED_PREFIX):
                issues.append(f"{did}: {pclass or 'unclassified'} dataset has a file in {GENERATED_PREFIX}")
            if root is not None and (root / f["path"]).suffix == ".csv" and (root / f["path"]).exists():
                with (root / f["path"]).open(encoding="utf-8-sig", newline="") as handle:
                    header = next(csv.reader(handle), [])
                if ORIGIN_COLUMN in header:
                    values = set(pd.read_csv(root / f["path"])[ORIGIN_COLUMN].astype(str))
                    if values & {"SIMULATED", "SYNTHETIC"}:
                        issues.append(f"{did}: observed dataset contains generated rows: {f['path']}")
    return issues


def collection_issues(root: Path, requirement_id: str) -> list[str]:
    """Generation is allowed only after every observed-data collection pathway was attempted."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import discovery  # noqa: E402
    reqs = {r.get("requirement_id"): r for r in discovery.read_csv(root / "data/requirements.csv")}
    req = reqs.get(requirement_id)
    if req is None:
        return [f"unknown requirement {requirement_id} in data/requirements.csv"]
    issues = []
    if discovery.placeholder(req.get("notes", "")):
        issues.append(f"{requirement_id} notes do not record why observed data could not be collected")
    types = {s.get("source_type") for s in discovery.read_csv(root / "data/source_search_log.csv")
             if requirement_id in discovery.ids(s.get("requirement_ids", ""))}
    for group in discovery.COLLECTION_GROUPS:
        if not types & discovery.PATHWAY_GROUPS[group]:
            issues.append(f"no {group} collection attempt for {requirement_id} in data/source_search_log.csv")
    return issues


def write_generated(root: Path, manifest_path: Path, data_id: str, frame: pd.DataFrame, filename: str,
                    pclass: str, generation: dict) -> str:
    if pclass not in GENERATED_CLASSES:
        raise SystemExit(f"[generate] provenance class must be one of {sorted(GENERATED_CLASSES)}")
    if generation.get("method") in RESAMPLING_METHODS and generation.get("within_reference_conditions") is not True:
        raise SystemExit("[generate] generation refused: resampling recombines observed rows and cannot represent "
                         "conditions absent from the reference (other season, climate, building). Use a calibrated "
                         "simulation or model and register it, or collect reference data for the target conditions.")
    blocked = collection_issues(root, generation.get("requirement_id", ""))
    if blocked:
        raise SystemExit("[generate] generation refused; collect first:\n  " + "\n  ".join(blocked))
    manifest = load_manifest(manifest_path)
    item = dataset(manifest, data_id)
    if item.get("provenance_class") in {"OBSERVED", "DERIVED"}:
        raise SystemExit(f"[generate] {data_id} is an observed dataset; register generated data under a new data_id")
    if ORIGIN_COLUMN not in frame.columns:
        if pclass == "AUGMENTED":
            raise SystemExit("[generate] AUGMENTED data must already label each row in a data_origin column")
        frame = frame.assign(**{ORIGIN_COLUMN: pclass})
    problems = check_origin_column(frame, pclass)
    if problems:
        raise SystemExit("[generate] " + "; ".join(problems))
    rel = f"{GENERATED_PREFIX}{data_id}/{filename}"
    target = root / rel
    if target.exists():
        raise SystemExit(f"[generate] {rel} exists; generated files are immutable. Use a new filename.")
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    target.chmod(target.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    digest = sha256_file(target)
    previous = item.get("generation", {})
    generation = {**previous, **{k: v for k, v in generation.items() if v not in (None, "")}}
    generation.setdefault("fidelity_criteria", previous.get("fidelity_criteria", []))
    generation.update(generated_at=now_iso(), validation_status="NOT_VALIDATED", validation_check_id="")
    sidecar = {"label": LABEL, "data_id": data_id, "provenance_class": pclass, "file": rel, "sha256": digest,
               "generation": generation}
    target.with_name(target.name + ".provenance.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    item.update(provenance_class=pclass, label=LABEL, generation=generation)
    item["files"] = [f for f in item.get("files", []) if f.get("path") and f["path"] != rel]
    item["files"].append({"path": rel, "sha256": digest, "bytes": target.stat().st_size})
    save_manifest(manifest_path, manifest)
    print(f"[generate] {rel} registered as {pclass} ({LABEL}) sha256={digest}")
    return rel


def generation_from_args(args: argparse.Namespace, method: str, parameters: dict) -> dict:
    return {"requirement_id": args.requirement_id, "method": method, "generator": args.generator, "generator_version": getattr(args, "generator_version", ""),
            "parameters": parameters, "seed": args.seed,
            "calibration_data_ids": [x for x in (args.calibration_data_ids or "").split(";") if x],
            "purpose": args.purpose, "reason_not_collected": args.reason_not_collected,
            "target_conditions": args.target_conditions,
            "within_reference_conditions": args.within_reference_conditions == "yes",
            "limitations": args.limitations, "generated_by": args.role}


def cmd_register(args: argparse.Namespace) -> int:
    frame = pd.read_csv(args.path)
    parameters = json.loads(args.parameters) if args.parameters else {}
    write_generated(Path(args.root), Path(args.manifest), args.data_id, frame, args.filename or Path(args.path).name,
                    args.provenance_class, generation_from_args(args, args.method, parameters))
    return 0


def block_bootstrap_frame(reference: pd.DataFrame, n_rows: int, block_length: int, seed: int,
                          timestamp_column: str = "", interval: str = "") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(reference)
    block_length = max(1, min(block_length, n))
    starts = rng.integers(0, n - block_length + 1, size=int(np.ceil(n_rows / block_length)))
    idx = (starts[:, None] + np.arange(block_length)[None, :]).ravel()[:n_rows]
    out = reference.iloc[idx].reset_index(drop=True)
    if timestamp_column and timestamp_column in out.columns:
        start = pd.to_datetime(reference[timestamp_column]).min()
        step = pd.Timedelta(interval) if interval else pd.to_datetime(reference[timestamp_column]).diff().median()
        out[timestamp_column] = [str(start + i * step) for i in range(n_rows)]
    return out.drop(columns=[ORIGIN_COLUMN], errors="ignore")


def cmd_bootstrap(args: argparse.Namespace) -> int:
    root, manifest_path = Path(args.root), Path(args.manifest)
    manifest = load_manifest(manifest_path)
    ref = dataset(manifest, args.reference_data_id)
    if is_generated(ref):
        raise SystemExit("[generate] bootstrap reference must be observed data, not generated data")
    ref_file = args.reference_file or next(f["path"] for f in ref.get("files", []) if f.get("path"))
    fmt = ref.get("format", {})
    ts = fmt.get("timestamp_column", "") if fmt.get("timestamp_column") not in ("TO_DEFINE", None) else ""
    reference = pd.read_csv(root / ref_file)
    if ts:
        reference = reference.sort_values(ts).reset_index(drop=True)
    frame = block_bootstrap_frame(reference, args.n_rows, args.block_length, args.seed, ts,
                                  fmt.get("expected_interval", "") if fmt.get("expected_interval") != "TO_DEFINE" else "")
    args.generator = "code/data/generate.py bootstrap (moving-block)"
    args.calibration_data_ids = args.reference_data_id
    params = {"block_length": args.block_length, "n_rows": args.n_rows, "reference_file": ref_file}
    write_generated(root, manifest_path, args.data_id, frame, args.filename, "SYNTHETIC",
                    generation_from_args(args, "BOOTSTRAP", params))
    return 0


def ks_statistic(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.sort(a), np.sort(b)
    grid = np.concatenate([a, b])
    cdf_a = np.searchsorted(a, grid, side="right") / len(a)
    cdf_b = np.searchsorted(b, grid, side="right") / len(b)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def acf1(x: np.ndarray) -> float:
    x = x - x.mean()
    denom = np.dot(x, x)
    return float(np.dot(x[1:], x[:-1]) / denom) if denom else 0.0


def fidelity_metrics(generated: pd.DataFrame, reference: pd.DataFrame, variable: str) -> dict:
    g = pd.to_numeric(generated[variable], errors="coerce").dropna().to_numpy()
    r = pd.to_numeric(reference[variable], errors="coerce").dropna().to_numpy()
    rmean, rstd = r.mean(), r.std(ddof=1)
    in_range = ((g >= r.min()) & (g <= r.max())).mean() if len(g) else 0.0
    return {
        "ks": ks_statistic(g, r),
        "mean_rel_diff": float(abs(g.mean() - rmean) / abs(rmean)) if rmean else float("nan"),
        "std_rel_diff": float(abs(g.std(ddof=1) - rstd) / rstd) if rstd else float("nan"),
        "acf_lag1_diff": abs(acf1(g) - acf1(r)),
        "range_coverage": float(in_range),
    }


def duplicate_rate(generated: pd.DataFrame, reference: pd.DataFrame, columns: list[str]) -> float:
    """Share of generated rows that copy a reference row exactly (memorization / leakage signal)."""
    if not columns or generated.empty:
        return 0.0
    ref_rows = set(map(tuple, reference[columns].round(9).astype(str).to_numpy()))
    gen_rows = list(map(tuple, generated[columns].round(9).astype(str).to_numpy()))
    return float(sum(row in ref_rows for row in gen_rows) / len(gen_rows))


def criterion_met(metric: str, value: float, crit: dict) -> bool:
    if "max" in crit and not value <= crit["max"]:
        return False
    if "min" in crit and not value >= crit["min"]:
        return False
    return "max" in crit or "min" in crit


def validate_frames(generated: pd.DataFrame, reference: pd.DataFrame, criteria: list[dict]) -> dict:
    numeric = [c for c in generated.columns if c in reference.columns and c != ORIGIN_COLUMN
               and pd.api.types.is_numeric_dtype(generated[c]) and pd.api.types.is_numeric_dtype(reference[c])]
    per_var = {v: fidelity_metrics(generated, reference, v) for v in numeric}
    dup = duplicate_rate(generated, reference, numeric)
    results, status = [], "PASS"
    if not criteria:
        status = "FAIL"
        results.append({"metric": "-", "passed": False, "note": "no pre-registered fidelity criteria"})
    for crit in criteria:
        metric, var = crit.get("metric"), crit.get("variable", "")
        if metric == "duplicate_rate":
            value = dup
        elif var in per_var:
            value = per_var[var][metric]
        else:
            results.append({**crit, "passed": False, "note": f"variable {var} not comparable"})
            status = "FAIL"
            continue
        passed = criterion_met(metric, value, crit)
        results.append({**crit, "value": value, "passed": passed})
        if not passed:
            status = "FAIL"
    return {"status": status, "criteria": results, "variables": per_var, "duplicate_rate": dup}


def cmd_validate(args: argparse.Namespace) -> int:
    root, manifest_path = Path(args.root), Path(args.manifest)
    manifest = load_manifest(manifest_path)
    item, ref = dataset(manifest, args.data_id), dataset(manifest, args.reference_data_id)
    if not is_generated(item):
        raise SystemExit(f"[generate] {args.data_id} is not generated data")
    if is_generated(ref):
        raise SystemExit("[generate] validate against observed reference data, not generated data")
    gen = item.get("generation", {})
    if args.role == gen.get("generated_by"):
        raise SystemExit("[generate] validation must be done by a role other than the generator")
    gen_file = next(f["path"] for f in item.get("files", []) if f.get("path"))
    ref_file = args.reference_file or next(f["path"] for f in ref.get("files", []) if f.get("path"))
    report = validate_frames(pd.read_csv(root / gen_file), pd.read_csv(root / ref_file), gen.get("fidelity_criteria", []))
    missing = [f for f in REQUIRED_GENERATION_FIELDS if gen.get(f) in (None, "", [], "TO_DEFINE")]
    if missing:
        report["status"] = "FAIL"
        report["criteria"].append({"metric": "generation_record", "passed": False,
                                   "note": "required generation fields missing: " + ", ".join(missing)})
    if gen.get("method") in RESAMPLING_METHODS and gen.get("within_reference_conditions") is not True:
        report["status"] = "FAIL"
        report["criteria"].append({"metric": "target_conditions", "passed": False,
                                   "note": "resampled data not confirmed to lie within the reference conditions"})
    notes = []
    if gen.get("within_reference_conditions") is False:
        notes.append("reference does not cover the target conditions; fidelity PASS shows similarity to the reference, "
                     "not representativeness of the target. Generated data cannot make a claim SUPPORTED.")
    if gen.get("method") in RESAMPLING_METHODS:
        notes.append("resampled rows copy the reference; do not evaluate on the reference with models trained on this "
                     "data (LEAKAGE check required when both are used).")
    report.update(notes=notes, target_conditions=gen.get("target_conditions"),
                  within_reference_conditions=gen.get("within_reference_conditions"))
    report.update(data_id=args.data_id, label=LABEL, generated_file=gen_file, reference_data_id=args.reference_data_id,
                  reference_file=ref_file, validated_by=args.role, validated_at=now_iso())
    output = Path(args.output or f"results/data_validation/{args.data_id}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gen["validation_status"] = report["status"]
    if args.record_check:
        gen["validation_check_id"] = args.record_check
        checks = Path(args.checks)
        with checks.open(encoding="utf-8-sig", newline="") as handle:
            fields = next(csv.reader(handle))
        with checks.open("a", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore").writerow({
                "check_id": args.record_check, "claim_id": "", "analysis_id": "", "data_id": args.data_id,
                "check_type": "GENERATED_DATA_VALIDATION",
                "description": f"fidelity of {LABEL} vs {args.reference_data_id}", "role": args.role,
                "artifact": str(output), "result": report["status"],
                "impact_on_claim": "" if report["status"] == "PASS" else "generated data failed fidelity; do not use",
                "checked_at": report["validated_at"],
            })
    save_manifest(manifest_path, manifest)
    for row in report["criteria"]:
        print(f"[generate] {row}")
    for note in notes:
        print(f"[generate] NOTE: {note}")
    print(f"[generate] {args.data_id} validation {report['status']} -> {output}")
    return 0 if report["status"] == "PASS" else 1


def disclosure_issues(root: Path, manuscript: Path) -> list[str]:
    manifest_path = root / "data/manifest.json"
    plan_path, claims_path = root / "evidence/analysis_plan.json", root / "evidence/claims.csv"
    if not (manifest_path.exists() and plan_path.exists() and claims_path.exists()):
        return []
    manifest = load_manifest(manifest_path)
    generated = {d["data_id"] for d in manifest.get("datasets", []) if is_generated(d)}
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    data_by_analysis = {a.get("analysis_id"): set(a.get("data_ids", [])) for a in plan.get("analyses", [])}
    with claims_path.open(encoding="utf-8-sig", newline="") as handle:
        claims = list(csv.DictReader(handle))
    used = set()
    for claim in claims:
        if claim.get("claim_status") in {"SUPPORTED", "PARTIALLY_SUPPORTED", "PRELIMINARY", "UNSUPPORTED"}:
            used |= data_by_analysis.get(claim.get("analysis_id"), set()) & generated
    text = manuscript.read_text(encoding="utf-8") if manuscript.exists() else ""
    disclosed = set(re.findall(r"\\GeneratedData\{([^}]+)\}", text))
    return [f"manuscript does not disclose generated dataset {d} with \\GeneratedData{{{d}}}" for d in sorted(used - disclosed)]


def cmd_check_disclosure(args: argparse.Namespace) -> int:
    issues = disclosure_issues(Path(args.root), Path(args.root) / args.manuscript)
    for issue in issues:
        print(f"[generate] {issue}")
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--manifest", default="data/manifest.json")
    common.add_argument("--root", default=".")
    gen_common = argparse.ArgumentParser(add_help=False)
    gen_common.add_argument("--data-id", required=True)
    gen_common.add_argument("--requirement-id", required=True,
                            help="data requirement this generated data stands in for (collection must have failed)")
    gen_common.add_argument("--seed", type=int, required=True)
    gen_common.add_argument("--purpose", required=True)
    gen_common.add_argument("--reason-not-collected", required=True,
                            help="which collection pathways failed and why (see data/source_search_log.csv)")
    gen_common.add_argument("--limitations", required=True)
    gen_common.add_argument("--target-conditions", required=True,
                            help="conditions the data must represent, e.g. 'office, January, heating season'")
    gen_common.add_argument("--within-reference-conditions", required=True, choices=["yes", "no"],
                            help="do the observed reference / calibration data cover the target conditions?")
    gen_common.add_argument("--role", default="Data Generator")
    reg = sub.add_parser("register", parents=[common, gen_common])
    reg.add_argument("--path", required=True)
    reg.add_argument("--filename")
    reg.add_argument("--provenance-class", required=True, choices=sorted(GENERATED_CLASSES))
    reg.add_argument("--method", required=True, choices=sorted(METHODS))
    reg.add_argument("--generator", required=True, help="tool/model and how to rerun it, e.g. 'EnergyPlus 24.2 model.idf'")
    reg.add_argument("--generator-version", default="")
    reg.add_argument("--parameters", help="JSON object of generation parameters")
    reg.add_argument("--calibration-data-ids", default="")
    reg.set_defaults(func=cmd_register)
    boot = sub.add_parser("bootstrap", parents=[common, gen_common])
    boot.add_argument("--reference-data-id", required=True)
    boot.add_argument("--reference-file")
    boot.add_argument("--n-rows", type=int, required=True)
    boot.add_argument("--block-length", type=int, required=True)
    boot.add_argument("--filename", default="bootstrap.csv")
    boot.set_defaults(func=cmd_bootstrap)
    val = sub.add_parser("validate", parents=[common])
    val.add_argument("--data-id", required=True)
    val.add_argument("--reference-data-id", required=True)
    val.add_argument("--reference-file")
    val.add_argument("--role", default="Generated Data Validator")
    val.add_argument("--output")
    val.add_argument("--record-check", metavar="CHECK_ID")
    val.add_argument("--checks", default="evidence/checks.csv")
    val.set_defaults(func=cmd_validate)
    dis = sub.add_parser("check-disclosure")
    dis.add_argument("--root", default=".")
    dis.add_argument("--manuscript", default="paper/body.tex")
    dis.set_defaults(func=cmd_check_disclosure)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
