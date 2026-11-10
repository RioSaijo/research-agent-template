"""Pre-use data quality profiling for tabular and time-series data (BMS/BEMS/IoT, meters, logs).

Implements the PROJECT.md pre-use checklist as machine checks against the variable
definitions in ``data/manifest.json``: declared columns and units, missing values,
duplicates, timestamp parsing, timezone, monotonicity, duplicate timestamps (DST),
sampling interval and gaps, coverage, physical range, flatline (stuck sensor), and
robust spike detection. Writes a JSON report and can append a DATA_QUALITY row to
``evidence/checks.csv`` so Gate 3 can use it.

Statuses: PASS (no findings), WARN (needs a documented judgement), FAIL (must be fixed
or the data excluded before confirmatory use).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

DEFAULT_THRESHOLDS = {
    "missing_warn": 0.02,
    "missing_fail": 0.20,
    "out_of_range_fail": 0.01,
    "spike_robust_z": 8.0,
    "gap_factor": 1.5,
    "interval_irregular_warn": 0.05,
}
SEVERITY = {"PASS": 0, "WARN": 1, "FAIL": 2}


def finding(level: str, check: str, message: str, **detail) -> dict:
    return {"level": level, "check": check, "message": message, **detail}


def longest_constant_run(values: pd.Series) -> int:
    values = values.dropna()
    if values.empty:
        return 0
    groups = (values != values.shift()).cumsum()
    return int(groups.value_counts().max())


def robust_spikes(values: pd.Series, z: float) -> int:
    diffs = values.dropna().diff().dropna()
    if len(diffs) < 10:
        return 0
    median = diffs.median()
    mad = (diffs - median).abs().median()
    if mad == 0:
        return 0
    robust_z = 0.6745 * (diffs - median).abs() / mad
    return int((robust_z > z).sum())


def profile_frame(frame: pd.DataFrame, dataset: dict, thresholds: dict | None = None) -> dict:
    th = {**DEFAULT_THRESHOLDS, **dataset.get("quality_thresholds", {}), **(thresholds or {})}
    fmt = dataset.get("format", {})
    findings: list[dict] = []
    variables = {v["name"]: v for v in dataset.get("variables", []) if v.get("name") not in (None, "", "TO_DEFINE")}
    ts_col = fmt.get("timestamp_column", "")
    ts_col = "" if ts_col in ("TO_DEFINE", None) else ts_col
    columns = set(frame.columns)

    for name in sorted(set(variables) - columns):
        findings.append(finding("FAIL", "declared_column", f"declared variable missing from data: {name}"))
    undeclared = sorted(columns - set(variables) - {ts_col})
    if undeclared:
        findings.append(finding("WARN", "undeclared_column", "columns not declared in manifest", columns=undeclared))

    dup_rows = int(frame.duplicated().sum())
    if dup_rows:
        findings.append(finding("WARN", "duplicate_rows", f"{dup_rows} fully duplicated rows", count=dup_rows))

    time_summary: dict = {}
    if ts_col:
        if ts_col not in columns:
            findings.append(finding("FAIL", "timestamp", f"timestamp column missing: {ts_col}"))
        else:
            raw = frame[ts_col]
            parsed = pd.to_datetime(raw, errors="coerce", utc=False, format=fmt.get("timestamp_format") or None)
            bad = int(parsed.isna().sum() - raw.isna().sum())
            if bad:
                findings.append(finding("FAIL", "timestamp_parse", f"{bad} unparseable timestamps", count=bad))
            if raw.isna().any():
                findings.append(finding("FAIL", "timestamp_missing", f"{int(raw.isna().sum())} missing timestamps"))
            tz = fmt.get("timezone", "")
            aware = getattr(parsed.dt, "tz", None) is not None
            if tz in ("", "TO_DEFINE", None) and not aware:
                findings.append(finding("FAIL", "timezone", "timezone undefined in manifest and timestamps are naive"))
            valid = parsed.dropna()
            dup_ts = int(valid.duplicated().sum())
            if dup_ts:
                findings.append(finding("FAIL", "duplicate_timestamp",
                                        f"{dup_ts} duplicate timestamps (check DST fall-back or merged exports)",
                                        count=dup_ts))
            if not valid.is_monotonic_increasing:
                findings.append(finding("WARN", "monotonic", "timestamps are not sorted ascending"))
            ordered = valid.sort_values().drop_duplicates()
            if len(ordered) >= 2:
                deltas = ordered.diff().dropna()
                median = deltas.median()
                expected = fmt.get("expected_interval", "")
                expected_td = pd.Timedelta(expected) if expected not in ("", "TO_DEFINE", None) else median
                if expected_td != median:
                    findings.append(finding("WARN", "interval", f"median interval {median} differs from expected {expected_td}"))
                irregular = float((deltas != expected_td).mean())
                if irregular > th["interval_irregular_warn"]:
                    findings.append(finding("WARN", "interval_irregular",
                                            f"{irregular:.1%} of intervals differ from {expected_td}", share=irregular))
                gaps = deltas[deltas > expected_td * th["gap_factor"]]
                if len(gaps):
                    missing_steps = int(((gaps / expected_td).round() - 1).sum())
                    findings.append(finding("WARN", "gaps", f"{len(gaps)} gaps, about {missing_steps} missing steps; "
                                            f"largest {gaps.max()}", count=int(len(gaps)), largest=str(gaps.max())))
                time_summary = {"start": str(ordered.iloc[0]), "end": str(ordered.iloc[-1]),
                                "median_interval": str(median), "expected_interval": str(expected_td)}
                coverage = dataset.get("coverage", {})
                for key, op in (("start", "after"), ("end", "before")):
                    bound = coverage.get(key, "")
                    if bound in ("", "TO_DEFINE", None):
                        continue
                    bound_ts = pd.Timestamp(bound)
                    actual = ordered.iloc[0] if key == "start" else ordered.iloc[-1]
                    try:
                        late = actual > bound_ts if key == "start" else actual < bound_ts
                    except TypeError:
                        findings.append(finding("WARN", "coverage", f"cannot compare coverage {key} (timezone mismatch)"))
                        continue
                    if late:
                        findings.append(finding("WARN", "coverage", f"data {key} {actual} is {op} declared {bound}"))

    var_summary: dict = {}
    n = len(frame)
    for name, var in variables.items():
        if name not in columns:
            continue
        series = frame[name]
        summary: dict = {"unit": var.get("unit", "")}
        missing = float(series.isna().mean()) if n else 0.0
        summary["missing_share"] = missing
        if missing > th["missing_fail"]:
            findings.append(finding("FAIL", "missing", f"{name}: {missing:.1%} missing", variable=name))
        elif missing > th["missing_warn"]:
            findings.append(finding("WARN", "missing", f"{name}: {missing:.1%} missing", variable=name))
        if var.get("dtype") in ("float", "int") and var.get("unit") in ("", "TO_DEFINE", None):
            findings.append(finding("FAIL", "unit", f"{name}: numeric variable has no unit in manifest", variable=name))
        if var.get("dtype") in ("float", "int"):
            numeric = pd.to_numeric(series, errors="coerce")
            non_numeric = int(numeric.isna().sum() - series.isna().sum())
            if non_numeric:
                findings.append(finding("FAIL", "dtype", f"{name}: {non_numeric} non-numeric values", variable=name))
            valid = numeric.dropna()
            if not valid.empty:
                summary.update({"min": float(valid.min()), "max": float(valid.max()),
                                "mean": float(valid.mean()), "std": float(valid.std(ddof=1)) if len(valid) > 1 else 0.0})
                low, high = var.get("min"), var.get("max")
                mask = pd.Series(False, index=valid.index)
                if isinstance(low, (int, float)):
                    mask |= valid < low
                if isinstance(high, (int, float)):
                    mask |= valid > high
                share = float(mask.mean())
                summary["out_of_range_share"] = share
                if share > th["out_of_range_fail"]:
                    findings.append(finding("FAIL", "range", f"{name}: {share:.1%} outside [{low}, {high}]", variable=name))
                elif share > 0:
                    findings.append(finding("WARN", "range", f"{name}: {int(mask.sum())} values outside [{low}, {high}]",
                                            variable=name))
                ordered = numeric
                if ts_col and ts_col in columns:
                    order = pd.to_datetime(frame[ts_col], errors="coerce").argsort(kind="stable")
                    ordered = numeric.iloc[order.to_numpy()].reset_index(drop=True)
                run = longest_constant_run(ordered)
                summary["longest_constant_run"] = run
                limit = var.get("max_flatline")
                if isinstance(limit, int) and run > limit:
                    findings.append(finding("WARN", "flatline", f"{name}: constant for {run} consecutive samples "
                                            f"(limit {limit}); possible stuck sensor", variable=name))
                spikes = robust_spikes(ordered, th["spike_robust_z"])
                summary["spikes"] = spikes
                if spikes:
                    findings.append(finding("WARN", "spike", f"{name}: {spikes} step changes with robust z > "
                                            f"{th['spike_robust_z']}", variable=name))
        var_summary[name] = summary

    status = max((f["level"] for f in findings), key=SEVERITY.get, default="PASS")
    return {"data_id": dataset.get("data_id", ""), "status": status, "rows": n, "columns": len(frame.columns),
            "thresholds": th, "time": time_summary, "variables": var_summary, "findings": findings}


def read_table(path: Path, fmt: dict) -> pd.DataFrame:
    kind = fmt.get("type", "csv")
    if kind == "parquet" or path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, sep=fmt.get("delimiter", ","), encoding=fmt.get("encoding", "utf-8-sig"))


def append_check(path: Path, row: dict) -> None:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        fieldnames = next(csv.reader(handle))
    with path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore").writerow(row)


def cmd_profile(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    dataset = next((d for d in manifest.get("datasets", []) if d.get("data_id") == args.data_id), None)
    if dataset is None:
        raise SystemExit(f"[quality] unknown data_id {args.data_id}")
    files = [args.file] if args.file else [f["path"] for f in dataset.get("files", []) if f.get("path")]
    if not files:
        raise SystemExit(f"[quality] {args.data_id} has no registered file")
    root = Path(args.root)
    reports = []
    for rel in files:
        path = root / rel
        report = profile_frame(read_table(path, dataset.get("format", {})), dataset)
        report["file"] = rel
        report["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        reports.append(report)
    status = max((r["status"] for r in reports), key=SEVERITY.get)
    output = Path(args.output or f"results/data_quality/{args.data_id}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    output.write_text(json.dumps({"data_id": args.data_id, "status": status, "generated_at": generated,
                                  "files": reports}, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    for report in reports:
        for item in report["findings"]:
            print(f"[quality] {args.data_id} {item['level']} {item['check']}: {item['message']}")
    print(f"[quality] {args.data_id}: {status} -> {output}")
    if args.record_check:
        result = {"PASS": "PASS", "WARN": "INCONCLUSIVE", "FAIL": "FAIL"}[status]
        append_check(Path(args.checks), {
            "check_id": args.record_check, "claim_id": args.claim_id or "", "analysis_id": args.analysis_id or "",
            "data_id": args.data_id, "check_type": "DATA_QUALITY",
            "description": "automated pre-use profile (code/data/quality.py)", "role": args.role,
            "artifact": str(output), "result": result,
            "impact_on_claim": "" if result == "PASS" else "要検討: review findings and record correction or exclusion",
            "checked_at": generated,
        })
    return {"PASS": 0, "WARN": 0, "FAIL": 1}[status]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    profile = sub.add_parser("profile")
    profile.add_argument("--data-id", required=True)
    profile.add_argument("--manifest", default="data/manifest.json")
    profile.add_argument("--root", default=".")
    profile.add_argument("--file", help="profile one file instead of all registered files")
    profile.add_argument("--output")
    profile.add_argument("--record-check", metavar="CHECK_ID", help="append a DATA_QUALITY row to evidence/checks.csv")
    profile.add_argument("--checks", default="evidence/checks.csv")
    profile.add_argument("--claim-id")
    profile.add_argument("--analysis-id")
    profile.add_argument("--role", default="Data Requirement")
    profile.set_defaults(func=cmd_profile)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
