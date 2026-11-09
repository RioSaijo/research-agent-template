"""Execute an analysis command and append its provenance to ``evidence/runs.csv``.

Usage:
  python code/analysis/record_run.py --run-id RUN-001 --analysis-id AN-01 --run-type PRIMARY \
      --role Analyst --seed 42 --inputs data/raw/DATA-01/x.csv --outputs results/metrics/an01.json \
      -- python code/analysis/an01.py

Guards for confirmatory runs (PRIMARY / REPRODUCTION / VERIFICATION / SENSITIVITY):
the analysis plan must be LOCKED, the analysis must exist, tracked files must be committed
(no uncommitted code), and inputs must exist. The child process receives RESEARCH_SEED and
PYTHONHASHSEED. Input hashes are taken before and checked after the run (inputs must not be
modified). A pip freeze snapshot is saved to results/environments/<run_id>.txt.
Failed commands are not recorded as evidence; the exit code is returned.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

FIELDS = ["run_id", "analysis_id", "run_type", "role", "run_at", "git_commit", "command", "environment",
          "seed", "inputs", "input_sha256", "outputs", "output_sha256", "input_data_origin", "notes"]
RUN_TYPES = {"PRIMARY", "REPRODUCTION", "VERIFICATION", "SENSITIVITY", "EXPLORATORY"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def split(value: str) -> list[str]:
    return [p.strip() for p in value.split(";") if p.strip()]


def input_origin(root: Path, inputs: list[str]) -> str:
    """Label the run with the origin of its input data (OBSERVED / GENERATED / MIXED / NOT_REGISTERED)."""
    if any(p.startswith("data/generated/") for p in inputs) and not (root / "data/manifest.json").exists():
        return "GENERATED"
    if not inputs or not (root / "data/manifest.json").exists():
        return "NOT_REGISTERED"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
    import generate  # noqa: E402
    manifest = json.loads((root / "data/manifest.json").read_text(encoding="utf-8"))
    return generate.path_origin(manifest, inputs)


def preflight(args: argparse.Namespace, root: Path) -> list[str]:
    issues: list[str] = []
    runs_path = root / args.runs
    if runs_path.exists():
        with runs_path.open(encoding="utf-8-sig", newline="") as handle:
            if any(r.get("run_id") == args.run_id for r in csv.DictReader(handle)):
                issues.append(f"run_id already recorded: {args.run_id}")
    for rel in split(args.inputs):
        if not (root / rel).is_file():
            issues.append(f"input missing: {rel}")
    if args.run_type == "EXPLORATORY":
        return issues
    plan = json.loads((root / args.plan).read_text(encoding="utf-8"))
    if plan.get("status") != "LOCKED":
        issues.append("analysis plan is not LOCKED; only EXPLORATORY runs are allowed")
    if args.analysis_id not in {a.get("analysis_id") for a in plan.get("analyses", [])}:
        issues.append(f"analysis_id not in plan: {args.analysis_id}")
    if not git(root, "rev-parse", "HEAD"):
        issues.append("not a git repository with commits; confirmatory runs need a commit")
    elif git(root, "status", "--porcelain", "--untracked-files=no") and not args.allow_dirty:
        issues.append("tracked files have uncommitted changes; commit code before a confirmatory run")
    if args.seed is None:
        issues.append("confirmatory run needs --seed (use 0 for deterministic code)")
    return issues


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    command = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not command:
        raise SystemExit("[record-run] no command given after --")
    issues = preflight(args, root)
    if issues:
        for issue in issues:
            print(f"[record-run] {issue}", file=sys.stderr)
        return 2
    inputs = split(args.inputs)
    before = [sha256_file(root / p) for p in inputs]
    run_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    env = dict(os.environ)
    if args.seed is not None:
        env.update({"RESEARCH_SEED": str(args.seed), "PYTHONHASHSEED": str(args.seed)})
    completed = subprocess.run(command, cwd=root, env=env)
    if completed.returncode != 0:
        print(f"[record-run] command failed with exit {completed.returncode}; run not recorded", file=sys.stderr)
        return completed.returncode
    after = [sha256_file(root / p) for p in inputs]
    changed = [p for p, a, b in zip(inputs, before, after) if a != b]
    if changed:
        print(f"[record-run] inputs modified by the run (raw data must be read-only): {changed}", file=sys.stderr)
        return 3
    outputs = split(args.outputs)
    missing = [p for p in outputs if not (root / p).is_file()]
    if missing:
        print(f"[record-run] declared outputs not produced: {missing}", file=sys.stderr)
        return 4
    env_rel = f"results/environments/{args.run_id}.txt"
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    env_path = root / env_rel
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        f"python {platform.python_version()} ({sys.executable})\nplatform {platform.platform()}\n\n"
        + (freeze.stdout if freeze.returncode == 0 else "pip freeze unavailable\n"),
        encoding="utf-8",
    )
    commit = git(root, "rev-parse", "HEAD")
    notes = args.notes
    if args.allow_dirty and git(root, "status", "--porcelain", "--untracked-files=no"):
        notes = (notes + "; " if notes else "") + "DIRTY_WORKTREE"
    row = {
        "run_id": args.run_id, "analysis_id": args.analysis_id, "run_type": args.run_type, "role": args.role,
        "run_at": run_at, "git_commit": commit, "command": " ".join(command),
        "environment": f"{env_rel} sha256={sha256_file(env_path)}",
        "seed": "" if args.seed is None else str(args.seed),
        "inputs": ";".join(inputs), "input_sha256": ";".join(before),
        "outputs": ";".join(outputs), "output_sha256": ";".join(sha256_file(root / p) for p in outputs),
        "input_data_origin": input_origin(root, inputs),
        "notes": notes,
    }
    runs_path = root / args.runs
    new_file = not runs_path.exists()
    with runs_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    if row["input_data_origin"] in {"GENERATED", "MIXED"}:
        print(f"[record-run] NOTE: inputs include generated data ({row['input_data_origin']}); outputs must be labeled as such")
    print(f"[record-run] recorded {args.run_id} ({args.run_type}) at {commit[:12] or 'no-commit'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--run-type", required=True, choices=sorted(RUN_TYPES))
    parser.add_argument("--role", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--inputs", default="", help="semicolon-separated repository-relative paths")
    parser.add_argument("--outputs", default="", help="semicolon-separated repository-relative paths")
    parser.add_argument("--notes", default="")
    parser.add_argument("--root", default=".")
    parser.add_argument("--plan", default="evidence/analysis_plan.json")
    parser.add_argument("--runs", default="evidence/runs.csv")
    parser.add_argument("--allow-dirty", action="store_true", help="record DIRTY_WORKTREE instead of refusing")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
