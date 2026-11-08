"""Data acquisition with provenance: download or register raw files, hash them, keep them read-only.

Raw data lives under ``data/raw/<DATA-ID>/`` (gitignored). ``data/manifest.json`` is the
committed, machine-readable data inventory: source, license, access class, acquisition,
file hashes, timestamp/timezone, sampling interval, variables with units and valid ranges.

Commands:
  fetch     download a URL into data/raw/<id>/ and record it
  register  record a file obtained by other means (BMS export, measurement, provided data)
  verify    validate the manifest and check that every raw file exists with the recorded hash
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PLACEHOLDER = "TO_DEFINE"
ACCESS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}
METHODS = {"DOWNLOAD", "API", "MANUAL_EXPORT", "BMS_EXPORT", "MEASUREMENT", "SIMULATION", "PROVIDED", "DERIVED"}
DTYPES = {"float", "int", "bool", "category", "string", "datetime"}
RAW_PREFIX = "data/raw/"
USER_AGENT = "research-agent-template/1.0 (data acquisition)"


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


def find_dataset(manifest: dict, data_id: str) -> dict:
    for dataset in manifest.get("datasets", []):
        if dataset.get("data_id") == data_id:
            return dataset
    raise SystemExit(f"[acquire] unknown data_id {data_id}; add it to data/manifest.json first")


def defined(value: object) -> bool:
    return value not in (None, "", PLACEHOLDER, [])


def make_read_only(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def record_file(dataset: dict, rel_path: str, digest: str, size: int) -> None:
    files = dataset.setdefault("files", [])
    files[:] = [f for f in files if f.get("path") and f.get("path") != rel_path]
    files.append({"path": rel_path, "sha256": digest, "bytes": size})


def place_raw(root: Path, data_id: str, source: Path, filename: str) -> tuple[str, str, int]:
    """Move or copy ``source`` into data/raw/<id>/<filename>; never overwrite different content."""
    rel = f"{RAW_PREFIX}{data_id}/{filename}"
    target = root / rel
    digest = sha256_file(source)
    if target.exists():
        if sha256_file(target) != digest:
            raise SystemExit(
                f"[acquire] {rel} exists with different content; raw data is immutable. "
                "Register the new version under a new filename or data_id."
            )
        return rel, digest, target.stat().st_size
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    make_read_only(target)
    return rel, digest, target.stat().st_size


def cmd_fetch(args: argparse.Namespace) -> int:
    root, manifest_path = Path(args.root), Path(args.manifest)
    manifest = load_manifest(manifest_path)
    dataset = find_dataset(manifest, args.data_id)
    filename = args.filename or Path(urllib.request.urlparse(args.url).path).name or "download"
    request = urllib.request.Request(args.url, headers={"User-Agent": USER_AGENT})
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp) / filename
        with urllib.request.urlopen(request, timeout=args.timeout) as response, temp.open("wb") as out:
            shutil.copyfileobj(response, out)
            final_url = response.geturl()
        rel, digest, size = place_raw(root, args.data_id, temp, filename)
    record_file(dataset, rel, digest, size)
    acquisition = dataset.setdefault("acquisition", {})
    if not defined(acquisition.get("method")):
        acquisition["method"] = "DOWNLOAD"
    acquisition.update({"url": final_url, "retrieved_at": now_iso(), "retrieved_by": args.role})
    save_manifest(manifest_path, manifest)
    print(f"[acquire] {rel} sha256={digest} bytes={size}")
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    root, manifest_path = Path(args.root), Path(args.manifest)
    manifest = load_manifest(manifest_path)
    dataset = find_dataset(manifest, args.data_id)
    source = Path(args.path)
    if not source.is_file():
        raise SystemExit(f"[acquire] not a file: {source}")
    rel, digest, size = place_raw(root, args.data_id, source, args.filename or source.name)
    record_file(dataset, rel, digest, size)
    acquisition = dataset.setdefault("acquisition", {})
    if args.method:
        acquisition["method"] = args.method
    acquisition.update({"retrieved_at": now_iso(), "retrieved_by": args.role})
    if args.source_note:
        acquisition["source_note"] = args.source_note
    save_manifest(manifest_path, manifest)
    print(f"[acquire] {rel} sha256={digest} bytes={size}")
    return 0


def validate_manifest(manifest: dict, root: Path | None, strict: bool) -> list[str]:
    issues: list[str] = []
    if manifest.get("schema_version") != "1.0.0":
        issues.append("unsupported data manifest schema_version")
    seen: set[str] = set()
    for dataset in manifest.get("datasets", []):
        did = dataset.get("data_id", "UNKNOWN")
        if did in seen:
            issues.append(f"{did}: duplicate data_id")
        seen.add(did)
        access = dataset.get("access", PLACEHOLDER)
        if defined(access) and access not in ACCESS:
            issues.append(f"{did}: invalid access class {access}")
        method = dataset.get("acquisition", {}).get("method", PLACEHOLDER)
        if defined(method) and method not in METHODS:
            issues.append(f"{did}: invalid acquisition method {method}")
        redistributable = dataset.get("redistributable")
        for item in dataset.get("files", []):
            rel = item.get("path", "")
            if not rel:
                continue
            if redistributable is not True and not rel.startswith(RAW_PREFIX):
                issues.append(f"{did}: non-redistributable file outside gitignored {RAW_PREFIX}: {rel}")
            if access in {"CONFIDENTIAL", "RESTRICTED"} and not rel.startswith(RAW_PREFIX):
                issues.append(f"{did}: {access} file outside {RAW_PREFIX}: {rel}")
            if root is None:
                continue
            target = root / rel
            if not target.exists():
                issues.append(f"{did}: raw file missing: {rel}")
            elif item.get("sha256") and sha256_file(target) != item["sha256"]:
                issues.append(f"{did}: raw file modified (hash mismatch): {rel}")
        fmt = dataset.get("format", {})
        for var in dataset.get("variables", []):
            name = var.get("name", "")
            dtype = var.get("dtype", PLACEHOLDER)
            if defined(dtype) and dtype not in DTYPES:
                issues.append(f"{did}: variable {name} has invalid dtype {dtype}")
            low, high = var.get("min"), var.get("max")
            if isinstance(low, (int, float)) and isinstance(high, (int, float)) and low > high:
                issues.append(f"{did}: variable {name} has min > max")
            if strict and defined(name) and dtype in {"float", "int"} and not defined(var.get("unit")):
                issues.append(f"{did}: numeric variable {name} has no unit")
        if strict:
            for field in ("title", "source", "owner", "access", "license"):
                if not defined(dataset.get(field)):
                    issues.append(f"{did}: field undefined: {field}")
            if not defined(method):
                issues.append(f"{did}: acquisition method undefined")
            if not [f for f in dataset.get("files", []) if f.get("path")]:
                issues.append(f"{did}: no raw file registered")
            if not dataset.get("related_rq"):
                issues.append(f"{did}: related_rq undefined")
            if defined(fmt.get("timestamp_column")) and not defined(fmt.get("timezone")):
                issues.append(f"{did}: timestamp column without timezone")
    return issues


def cmd_verify(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    root = None if args.skip_files else Path(args.root)
    issues = validate_manifest(manifest, root, strict=not args.allow_incomplete)
    for issue in issues:
        print(f"[data-verify] {issue}")
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--manifest", default="data/manifest.json")
    common.add_argument("--root", default=".")
    fetch = sub.add_parser("fetch", parents=[common])
    fetch.add_argument("--data-id", required=True)
    fetch.add_argument("--url", required=True)
    fetch.add_argument("--filename")
    fetch.add_argument("--role", default="Data Requirement")
    fetch.add_argument("--timeout", type=float, default=120)
    fetch.set_defaults(func=cmd_fetch)
    register = sub.add_parser("register", parents=[common])
    register.add_argument("--data-id", required=True)
    register.add_argument("--path", required=True)
    register.add_argument("--filename")
    register.add_argument("--method", choices=sorted(METHODS))
    register.add_argument("--source-note", help="non-secret note on origin, e.g. BMS export screen and date range")
    register.add_argument("--role", default="Data Requirement")
    register.set_defaults(func=cmd_register)
    verify = sub.add_parser("verify", parents=[common])
    verify.add_argument("--allow-incomplete", action="store_true")
    verify.add_argument("--skip-files", action="store_true", help="validate structure only (CI without raw data)")
    verify.set_defaults(func=cmd_verify)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    os.umask(0o022)
    raise SystemExit(main())
