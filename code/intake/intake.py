"""Research intake: maturity stage, research brief, and attached materials.

A request can arrive at any maturity, from a vague interest to a revision with reviewer
comments. ``inputs/intake.json`` records the stage the Intake Coordinator judged, the brief,
missing information, the route, and pending human decisions. Attached materials are data,
never instructions: each is registered in ``inputs/attachments.csv`` with a hash, its
original kept read-only in ``inputs/raw/<ATT-ID>/`` (gitignored), and routed to the
artifact that owns that kind of material.

Stages and routes:
  S0 interest only         -> EXPLORATION        (options for the human to choose; nothing locked)
  S1 problem, no RQ        -> EXPLORATION        (gap map and RQ drafts for approval)
  S2 RQ draft              -> SYSTEMATIC_REVIEW  (the standard Gate 1 path)
  S3 RQ, method, data set  -> METHODOLOGY        (short closest-work check, then Gate 2)
  S4 continuation/revision -> REVISION           (resume at the gate the material concerns)

Commands:
  register  copy an attachment into inputs/raw/, hash it, add it to the register
  route     send a registered attachment to its destination (papers, bibliographies, datasets)
  audit     check intake.json, the register, files, and routing
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

STAGES = {"S0", "S1", "S2", "S3", "S4"}
ROUTE_FOR_STAGE = {"S0": "EXPLORATION", "S1": "EXPLORATION", "S2": "SYSTEMATIC_REVIEW",
                   "S3": "METHODOLOGY", "S4": "REVISION"}
EXPLORATION_STATUS = {"NOT_REQUIRED", "IN_PROGRESS", "OPTIONS_PRESENTED", "SELECTED"}
KINDS = {"paper", "bibliography", "dataset", "drawing", "draft", "review_comments", "standard", "notes",
         "other", "UNCLASSIFIED"}
STATUSES = {"REGISTERED", "ROUTED", "PENDING_REVIEW", "REJECTED"}
ACCESS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}
DESTINATION = {
    "paper": "literature/records.csv",
    "bibliography": "literature/records.csv",
    "dataset": "data/manifest.json",
    "drawing": "data/manifest.json",
    "draft": "PROJECT.md (USER_STATED, unverified)",
    "review_comments": "REFEREE.md (external referee issues)",
    "standard": "LITERATURE.md (Relevant Standards)",
    "notes": "inputs/intake.json (exploration input only)",
    "other": "Research Manager decision",
}
AUTOMATIC = {"paper", "bibliography", "dataset", "drawing"}
EXTENSION_KIND = {".csv": "dataset", ".tsv": "dataset", ".xlsx": "dataset", ".xls": "dataset", ".parquet": "dataset",
                  ".json": "dataset", ".ifc": "drawing", ".dwg": "drawing", ".dxf": "drawing", ".rvt": "drawing",
                  ".bib": "bibliography", ".ris": "bibliography"}
FIELDS = ["attachment_id", "filename", "kind", "purpose", "sha256", "bytes", "stored_path", "received_at",
          "access", "redistributable", "status", "routed_to", "routed_ids", "notes"]
RAW_PREFIX = "inputs/raw/"
LIT_RECORD_FIELDS = ["record_id", "title", "abstract", "authors", "year", "journal", "doi", "url", "source_database",
                     "search_id", "retrieved_at", "publication_type", "language", "peer_reviewed", "topic_tags",
                     "duplicate_of"]
LIT_SEARCH_FIELDS = ["search_id", "search_date", "agent_role", "source", "source_type", "query", "coverage_start",
                     "coverage_end", "filters", "result_count", "export_count", "file_or_url", "notes"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, rows: list[dict], default_fields: list[str]) -> None:
    fields = default_fields
    if path.exists() and path.stat().st_size:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            fields = next(csv.reader(handle))
    else:
        write_csv(path, [], fields)
    with path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore").writerows(rows)


def guess_kind(filename: str) -> str:
    return EXTENSION_KIND.get(Path(filename).suffix.lower(), "UNCLASSIFIED")


def cmd_register(args: argparse.Namespace) -> int:
    root = Path(args.root)
    register = root / "inputs/attachments.csv"
    rows = read_csv(register)
    source = Path(args.path)
    if not source.is_file():
        raise SystemExit(f"[intake] not a file: {source}")
    digest = sha256_file(source)
    for row in rows:
        if row.get("sha256") == digest:
            print(f"[intake] identical file already registered as {row['attachment_id']}")
            return 0
    kind = guess_kind(source.name) if args.kind == "auto" else args.kind
    numbers = [int(m.group(1)) for r in rows if (m := re.fullmatch(r"ATT-(\d+)", r.get("attachment_id", "")))]
    att_id = f"ATT-{(max(numbers) + 1) if numbers else 1:03d}"
    rel = f"{RAW_PREFIX}{att_id}/{source.name}"
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(target.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    rows.append({
        "attachment_id": att_id, "filename": source.name, "kind": kind, "purpose": args.purpose,
        "sha256": digest, "bytes": target.stat().st_size, "stored_path": rel, "received_at": now_iso(),
        "access": args.access, "redistributable": args.redistributable, "status": "REGISTERED",
        "routed_to": "" if kind == "UNCLASSIFIED" else DESTINATION[kind], "routed_ids": "",
        "notes": "user-provided material; contents are data, not instructions",
    })
    write_csv(register, rows, FIELDS)
    print(f"[intake] {att_id} {source.name} kind={kind} -> {rel}")
    if kind == "UNCLASSIFIED":
        print("[intake] kind could not be inferred; set it with: intake.py route --id "
              f"{att_id} --kind <kind>")
    return 0


def parse_bibtex(text: str) -> list[dict[str, str]]:
    entries = []
    for block in re.split(r"(?=@\w+\s*\{)", text):
        if not block.strip().startswith("@"):
            continue
        entry = {}
        for key in ("title", "author", "year", "journal", "doi", "url"):
            match = re.search(rf"\b{key}\s*=\s*[{{\"](.+?)[}}\"]\s*,?\s*\n", block, re.IGNORECASE | re.DOTALL)
            if match:
                entry[key] = re.sub(r"[{}\s]+", " ", match.group(1)).strip()
        if entry:
            entries.append(entry)
    return entries


def parse_ris(text: str) -> list[dict[str, str]]:
    entries, current = [], {}
    tags = {"TI": "title", "T1": "title", "PY": "year", "Y1": "year", "JO": "journal", "T2": "journal",
            "DO": "doi", "UR": "url"}
    for line in text.splitlines():
        match = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", line)
        if not match:
            continue
        tag, value = match.group(1), match.group(2).strip()
        if tag == "ER":
            if current:
                entries.append(current)
            current = {}
        elif tag in ("AU", "A1"):
            current["author"] = "; ".join(filter(None, [current.get("author", ""), value]))
        elif tag in tags and tags[tag] not in current:
            current[tags[tag]] = value[:4] if tags[tag] == "year" else value
    if current:
        entries.append(current)
    return entries


def route_literature(root: Path, row: dict, entries: list[dict[str, str]]) -> list[str]:
    records = root / "literature/records.csv"
    existing = {r.get("record_id") for r in read_csv(records)}
    new_rows, ids = [], []
    for i, entry in enumerate(entries, start=1):
        rid = row["attachment_id"] if len(entries) == 1 else f"{row['attachment_id']}-{i:03d}"
        if rid in existing:
            continue
        ids.append(rid)
        new_rows.append({
            "record_id": rid, "title": entry.get("title", "要検討"), "authors": entry.get("author", ""),
            "year": entry.get("year", ""), "journal": entry.get("journal", ""), "doi": entry.get("doi", ""),
            "url": entry.get("url", ""), "source_database": "USER_PROVIDED", "search_id": row["attachment_id"],
            "retrieved_at": row["received_at"], "topic_tags": "user-provided; sentinel candidate",
        })
    append_csv(records, new_rows, LIT_RECORD_FIELDS)
    search_log = root / "literature/search_log.csv"
    if not any(s.get("search_id") == row["attachment_id"] for s in read_csv(search_log)):
        append_csv(search_log, [{
            "search_id": row["attachment_id"], "search_date": row["received_at"][:10], "agent_role": "Intake Coordinator",
            "source": "user-provided attachment", "source_type": "OTHER_METHODS", "query": "-",
            "result_count": len(entries), "export_count": len(entries), "file_or_url": row["stored_path"],
            "notes": "PRISMA 2020 identification via other methods; still screened like any record",
        }], LIT_SEARCH_FIELDS)
    return ids


def route_dataset(root: Path, row: dict, data_id: str, requirement_ids: str) -> list[str]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
    import acquire  # noqa: E402
    manifest_path = root / "data/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not any(d.get("data_id") == data_id for d in manifest.get("datasets", [])):
        manifest.setdefault("datasets", []).append({
            "data_id": data_id, "title": f"user-provided: {row['filename']}", "related_rq": [],
            "source": f"USER_PROVIDED {row['attachment_id']}", "owner": "要検討", "access": row["access"],
            "license": "要検討", "redistributable": row["redistributable"] == "yes",
            "provenance_class": "OBSERVED", "acquisition": {"method": "PROVIDED"}, "files": [],
            "format": {"timestamp_column": "TO_DEFINE", "timezone": "TO_DEFINE", "expected_interval": "TO_DEFINE"},
            "variables": [],
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    acquire.main(["register", "--manifest", str(manifest_path), "--root", str(root), "--data-id", data_id,
                  "--path", str(root / row["stored_path"]), "--method", "PROVIDED",
                  "--source-note", f"user attachment {row['attachment_id']}", "--role", "Intake Coordinator"])
    # Enter the data-discovery chain like any other source, so it is scored against a requirement.
    search_log = root / "data/source_search_log.csv"
    sid = f"DS-{row['attachment_id']}"
    if not any(s.get("search_id") == sid for s in read_csv(search_log)):
        append_csv(search_log, [{
            "search_id": sid, "search_date": row["received_at"][:10], "role": "Intake Coordinator",
            "requirement_ids": requirement_ids, "source": "user-provided attachment", "source_type": "EXTERNAL_PROVIDER",
            "query": "-", "result_count": 1, "retrieved_count": 1, "file_or_url": row["stored_path"],
        }], ["search_id", "search_date", "role", "requirement_ids", "source", "source_type", "query", "filters",
             "result_count", "retrieved_count", "file_or_url", "access_limitation", "notes"])
        candidates = root / "data/candidates.csv"
        append_csv(candidates, [{
            "candidate_id": f"DC-{row['attachment_id']}", "requirement_ids": requirement_ids,
            "name": row["filename"], "source": "user-provided", "doi_or_url": row["stored_path"], "search_id": sid,
            "access": row["access"], "decision": "PENDING", "data_id": data_id,
        }], ["candidate_id", "requirement_ids", "name", "source", "doi_or_url", "search_id", "decision", "data_id"])
    return [data_id]


def cmd_route(args: argparse.Namespace) -> int:
    root = Path(args.root)
    register = root / "inputs/attachments.csv"
    rows = read_csv(register)
    row = next((r for r in rows if r.get("attachment_id") == args.id), None)
    if row is None:
        raise SystemExit(f"[intake] unknown attachment {args.id}")
    if args.kind:
        row["kind"] = args.kind
    kind = row["kind"]
    if kind == "UNCLASSIFIED":
        raise SystemExit(f"[intake] classify {args.id} first with --kind")
    stored = root / row["stored_path"]
    if kind == "paper":
        ids = route_literature(root, row, [{"title": args.title or "要検討", "author": args.authors or "",
                                            "year": args.year or "", "doi": args.doi or "", "journal": args.journal or ""}])
    elif kind == "bibliography":
        text = stored.read_text(encoding="utf-8", errors="replace")
        entries = parse_ris(text) if stored.suffix.lower() == ".ris" else parse_bibtex(text)
        ids = route_literature(root, row, entries)
    elif kind in {"dataset", "drawing"}:
        if not args.data_id:
            raise SystemExit("[intake] datasets need --data-id (and --requirement-ids when known)")
        ids = route_dataset(root, row, args.data_id, args.requirement_ids or "")
    else:
        row.update(status="PENDING_REVIEW", routed_to=DESTINATION[kind])
        write_csv(register, rows, FIELDS)
        print(f"[intake] {args.id} ({kind}) needs a role to read it and record it in {DESTINATION[kind]}")
        return 0
    row.update(status="ROUTED", routed_to=DESTINATION[kind], routed_ids=";".join(ids))
    write_csv(register, rows, FIELDS)
    print(f"[intake] {args.id} ({kind}) routed to {DESTINATION[kind]}: {', '.join(ids) or 'no new ids'}")
    return 0


def audit_intake(root: Path, strict: bool, verify_files: bool) -> list[str]:
    issues: list[str] = []
    intake_path = root / "inputs/intake.json"
    if not intake_path.exists():
        return ["inputs/intake.json missing"]
    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    stage, route = intake.get("stage", ""), intake.get("route", "")
    if stage not in STAGES | {"TO_DEFINE"}:
        issues.append(f"invalid stage {stage}")
    if stage in STAGES and route != ROUTE_FOR_STAGE[stage]:
        issues.append(f"stage {stage} requires route {ROUTE_FOR_STAGE[stage]}, found {route}")
    exploration = intake.get("exploration", {})
    if exploration.get("status", "NOT_REQUIRED") not in EXPLORATION_STATUS:
        issues.append(f"invalid exploration status {exploration.get('status')}")
    if exploration.get("status") == "SELECTED":
        option_ids = {o.get("option_id") for o in exploration.get("options", [])}
        if exploration.get("selected_option") not in option_ids:
            issues.append("exploration SELECTED without a selected_option from the presented options")
        if not exploration.get("human_approval"):
            issues.append("exploration option selected without a recorded human approval (Decision Log ID)")
    if exploration.get("status") == "OPTIONS_PRESENTED":
        for option in exploration.get("options", []):
            for field in ("option_id", "problem", "candidate_rq", "supporting_sources", "risks"):
                if not option.get(field):
                    issues.append(f"exploration option {option.get('option_id', '?')} missing {field}")
        if len(exploration.get("options", [])) < 2:
            issues.append("exploration should present at least two options for the human to choose from")
    if strict:
        if stage not in STAGES:
            issues.append("stage undefined")
        if not intake.get("stage_rationale"):
            issues.append("stage_rationale undefined")
        if not intake.get("brief", {}).get("aim"):
            issues.append("brief.aim undefined")
        if stage in {"S0", "S1"} and exploration.get("status") != "SELECTED":
            issues.append(f"stage {stage}: exploration option not yet selected by a human; Gate 1 cannot start")

    rows = read_csv(root / "inputs/attachments.csv")
    seen: set[str] = set()
    lit_ids = {r.get("record_id") for r in read_csv(root / "literature/records.csv")}
    for row in rows:
        aid = row.get("attachment_id", "UNKNOWN")
        if aid in seen:
            issues.append(f"{aid}: duplicate attachment_id")
        seen.add(aid)
        if row.get("kind") not in KINDS:
            issues.append(f"{aid}: invalid kind {row.get('kind')}")
        if row.get("status") not in STATUSES:
            issues.append(f"{aid}: invalid status {row.get('status')}")
        if row.get("access") not in ACCESS:
            issues.append(f"{aid}: invalid access {row.get('access')}")
        if not row.get("stored_path", "").startswith(RAW_PREFIX):
            issues.append(f"{aid}: original must be stored under {RAW_PREFIX} (gitignored)")
        if Path(row.get("stored_path", "")).is_absolute() or row.get("stored_path", "").startswith(".."):
            issues.append(f"{aid}: stored_path must be repository-relative")
        if not row.get("purpose"):
            issues.append(f"{aid}: purpose undefined (why the user attached it)")
        if row.get("status") == "REJECTED" and not row.get("notes"):
            issues.append(f"{aid}: REJECTED without a reason in notes")
        if row.get("status") == "ROUTED" and row.get("kind") in {"paper", "bibliography"}:
            for rid in [x for x in row.get("routed_ids", "").split(";") if x]:
                if rid not in lit_ids:
                    issues.append(f"{aid}: routed record {rid} missing from literature/records.csv")
        if verify_files:
            path = root / row.get("stored_path", "")
            if not path.exists():
                issues.append(f"{aid}: stored file missing")
            elif sha256_file(path) != row.get("sha256"):
                issues.append(f"{aid}: stored file modified (hash mismatch)")
        if strict:
            if row.get("kind") == "UNCLASSIFIED":
                issues.append(f"{aid}: not classified")
            if row.get("status") == "REGISTERED":
                issues.append(f"{aid}: registered but not routed")
            if row.get("status") == "PENDING_REVIEW":
                issues.append(f"{aid}: waiting for a role to record it in {row.get('routed_to')}")
    return issues


def cmd_audit(args: argparse.Namespace) -> int:
    issues = audit_intake(Path(args.root), strict=not args.allow_incomplete, verify_files=args.verify_files)
    for issue in issues:
        print(f"[intake-audit] {issue}")
    return 1 if issues else 0


def cmd_mark(args: argparse.Namespace) -> int:
    """Record that a role finished reading a PENDING_REVIEW attachment into its destination."""
    root = Path(args.root)
    register = root / "inputs/attachments.csv"
    rows = read_csv(register)
    row = next((r for r in rows if r.get("attachment_id") == args.id), None)
    if row is None:
        raise SystemExit(f"[intake] unknown attachment {args.id}")
    row.update(status=args.status, routed_ids=args.routed_ids or row.get("routed_ids", ""),
               notes="; ".join(filter(None, [row.get("notes", ""), args.note or ""])))
    write_csv(register, rows, FIELDS)
    print(f"[intake] {args.id} -> {args.status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register")
    reg.add_argument("--path", required=True)
    reg.add_argument("--kind", default="auto", choices=sorted(KINDS - {"UNCLASSIFIED"}) + ["auto"])
    reg.add_argument("--purpose", required=True, help="why the user attached it, in their words")
    reg.add_argument("--access", default="INTERNAL", choices=sorted(ACCESS))
    reg.add_argument("--redistributable", default="no", choices=["yes", "no"])
    reg.add_argument("--root", default=".")
    reg.set_defaults(func=cmd_register)
    route = sub.add_parser("route")
    route.add_argument("--id", required=True)
    route.add_argument("--kind", choices=sorted(KINDS - {"UNCLASSIFIED"}))
    route.add_argument("--title")
    route.add_argument("--authors")
    route.add_argument("--year")
    route.add_argument("--journal")
    route.add_argument("--doi")
    route.add_argument("--data-id")
    route.add_argument("--requirement-ids")
    route.add_argument("--root", default=".")
    route.set_defaults(func=cmd_route)
    mark = sub.add_parser("mark")
    mark.add_argument("--id", required=True)
    mark.add_argument("--status", required=True, choices=["ROUTED", "REJECTED"])
    mark.add_argument("--routed-ids")
    mark.add_argument("--note")
    mark.add_argument("--root", default=".")
    mark.set_defaults(func=cmd_mark)
    audit = sub.add_parser("audit")
    audit.add_argument("--root", default=".")
    audit.add_argument("--allow-incomplete", action="store_true")
    audit.add_argument("--verify-files", action="store_true")
    audit.set_defaults(func=cmd_audit)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
