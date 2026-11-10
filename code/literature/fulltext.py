"""Full-text access: find, obtain, and track the full text of literature records.

Many papers cannot be read automatically (paywalls, publisher bot protection). This module
gets what can be obtained, asks the user only for the rest in one batch, and records the
state of every record so its use can be limited when the full text stays unavailable.

Ledger: ``literature/fulltext.csv``. Downloaded files: ``literature/fulltext/`` (gitignored);
user-downloaded PDFs are registered as attachments (``inputs/raw/``) through intake.py.

Statuses:
  NEEDED            full text required, not yet obtained
  MANUAL_REQUESTED  listed for the user to download in a browser (``manual-list``)
  AVAILABLE         file obtained (open access or user-provided), not yet read
  READ              a role read it; ``location_read`` records what was read
  ABSTRACT_ONLY     not obtainable after the attempts below; only the abstract is used
  METADATA_ONLY     not obtainable and no abstract; only bibliographic data is used
  UNAVAILABLE       not obtainable; the record cannot be assessed at full text

Use limits (enforced by ``audit``): only READ records support extraction, central claims,
numeric values, method details, and gap evidence; ABSTRACT_ONLY records may inform
title/abstract screening and the evidence map; a full-text exclusion for NO_FULL_TEXT
requires UNAVAILABLE after an open-access attempt and a manual request; CRITICAL records
that are not READ need a recorded human decision.

Commands:
  queue        add records that need full text (advanced at title/abstract, or given as CRITICAL)
  fetch-oa     try open-access copies listed by OpenAlex for NEEDED records
  manual-list  write the browser download list for the user and mark those records MANUAL_REQUESTED
  import       match user-downloaded PDFs in a folder by DOI and register them
  mark-read    record that a role read the full text, with the location read
  finalize     close a record that could not be obtained (ABSTRACT_ONLY / METADATA_ONLY / UNAVAILABLE)
  audit        check the ledger against screening, extraction, and files
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

STATUSES = ["NEEDED", "MANUAL_REQUESTED", "AVAILABLE", "READ", "ABSTRACT_ONLY", "METADATA_ONLY", "UNAVAILABLE"]
CLOSED_UNREAD = {"ABSTRACT_ONLY", "METADATA_ONLY", "UNAVAILABLE"}
PRIORITIES = ["CRITICAL", "HIGH", "NORMAL"]
REASONS = {"FULL_TEXT_SCREENING", "CRITICAL", "EXTRACTION", "CLAIM_SUPPORT", "CITATION_SEED"}
FIELDS = ["record_id", "doi", "title", "priority", "need_reason", "status", "source", "stored_path", "sha256",
          "oa_attempted_at", "manual_requested_at", "attempts", "location_read", "read_by", "human_decision", "notes"]
LEDGER = "literature/fulltext.csv"
STORE = "literature/fulltext/"
USER_AGENT = "research-agent-template/1.0 (open-access full-text retrieval)"
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
Fetcher = Callable[[str], tuple[int, str, bytes]]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.rstrip(" .;,)")


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


def write_ledger(root: Path, rows: list[dict]) -> None:
    path = root / LEDGER
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_attempt(row: dict, text: str) -> None:
    row["attempts"] = "; ".join(filter(None, [row.get("attempts", ""), f"{now_iso()[:10]} {text}"]))


def advanced_records(root: Path) -> set[str]:
    """Records whose title/abstract outcome advances them to full-text screening."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import systematic_review  # noqa: E402
    grouped: dict[str, list[dict]] = {}
    for row in read_csv(root / "literature/screening_decisions.csv"):
        if row.get("stage") == "TITLE_ABSTRACT":
            grouped.setdefault(row.get("record_id", ""), []).append(row)
    return {rid for rid, rows in grouped.items() if systematic_review.stage_result("TITLE_ABSTRACT", rows)[0] == "ADVANCE"}


def cmd_queue(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ledger = read_csv(root / LEDGER)
    by_id = {r["record_id"]: r for r in ledger}
    records = {r.get("record_id"): r for r in read_csv(root / "literature/records.csv")
               if not r.get("duplicate_of")}
    wanted: dict[str, tuple[str, str]] = {}
    if not args.no_screening:
        for rid in advanced_records(root):
            wanted[rid] = ("HIGH", "FULL_TEXT_SCREENING")
    for rid in [x for x in (args.record_ids or "").split(";") if x]:
        wanted[rid] = (args.priority, args.reason)
    added = upgraded = 0
    for rid, (priority, reason) in wanted.items():
        rec = records.get(rid)
        if rec is None:
            print(f"[fulltext] skip unknown or duplicate record {rid}")
            continue
        if rid in by_id:
            row = by_id[rid]
            if PRIORITIES.index(priority) < PRIORITIES.index(row.get("priority") or "NORMAL"):
                row.update(priority=priority, need_reason=reason)
                upgraded += 1
            continue
        row = {"record_id": rid, "doi": canonical_doi(rec.get("doi", "")), "title": rec.get("title", ""),
               "priority": priority, "need_reason": reason, "status": "NEEDED"}
        if rec.get("source_database") == "USER_PROVIDED":
            att = next((a for a in read_csv(root / "inputs/attachments.csv")
                        if a.get("attachment_id") == rec.get("search_id") and a.get("kind") == "paper"), None)
            if att:
                row.update(status="AVAILABLE", source=f"USER_PROVIDED {att['attachment_id']}",
                           stored_path=att["stored_path"], sha256=att["sha256"])
        ledger.append(row)
        by_id[rid] = row
        added += 1
    write_ledger(root, ledger)
    print(f"[fulltext] queued {added} new, raised priority of {upgraded}; ledger has {len(ledger)} records")
    return 0


def http_get(url: str) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read(60 * 1024 * 1024)


def oa_locations(doi: str, fetch: Fetcher) -> list[str]:
    _, _, body = fetch("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
    work = json.loads(body)
    urls = []
    for loc in work.get("locations", []):
        if loc.get("is_oa"):
            for key in ("pdf_url", "landing_page_url"):
                if loc.get(key) and loc[key] not in urls:
                    urls.append(loc[key])
    return urls


def cmd_fetch_oa(args: argparse.Namespace, fetch: Fetcher = http_get) -> int:
    root = Path(args.root)
    ledger = read_csv(root / LEDGER)
    blocked: Counter = Counter()
    got = 0
    for row in ledger:
        if row.get("status") not in {"NEEDED", "MANUAL_REQUESTED"} or not row.get("doi"):
            continue
        row["oa_attempted_at"] = now_iso()
        try:
            urls = oa_locations(row["doi"], fetch)
        except Exception as exc:  # noqa: BLE001 - record any lookup failure as an attempt
            add_attempt(row, f"openalex lookup failed: {str(exc)[:60]}")
            continue
        if not urls:
            add_attempt(row, "no open-access copy listed by OpenAlex")
            continue
        for url in urls:
            host = urllib.parse.urlparse(url).netloc
            try:
                status, ctype, body = fetch(url)
            except urllib.error.HTTPError as exc:
                add_attempt(row, f"{host} HTTP {exc.code}")
                continue
            except Exception as exc:  # noqa: BLE001
                reason = "network policy" if "403" in str(exc) and "Tunnel" in str(exc) else str(exc)[:50]
                if reason == "network policy":
                    blocked[host] += 1
                add_attempt(row, f"{host} {reason}")
                continue
            if body[:5] != b"%PDF-":
                add_attempt(row, f"{host} {status} not a PDF ({ctype.split(';')[0]})")
                continue
            rel = f"{STORE}{re.sub(r'[^A-Za-z0-9_.-]', '_', row['record_id'])}.pdf"
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            target.chmod(target.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            row.update(status="AVAILABLE", source=url, stored_path=rel, sha256=sha256_file(target))
            add_attempt(row, f"{host} OK open-access PDF")
            got += 1
            break
    write_ledger(root, ledger)
    print(f"[fulltext] open-access PDFs obtained: {got}")
    if blocked:
        print("[fulltext] hosts refused by the network policy (consider allowing): "
              + ", ".join(f"{h} ({n})" for h, n in blocked.most_common()))
    return 0


def cmd_manual_list(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ledger = read_csv(root / LEDGER)
    pending = [r for r in ledger if r.get("status") in {"NEEDED", "MANUAL_REQUESTED"}]
    pending.sort(key=lambda r: (PRIORITIES.index(r.get("priority") or "NORMAL"), r["record_id"]))
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Full texts to download", "",
             "Open each link in your browser on the university network, save the PDF into one folder,",
             "and hand the folder back. File names do not matter: PDFs are matched by DOI.", "",
             "| # | Priority | Record | Title | Link |", "|---|---|---|---|---|"]
    for i, r in enumerate(pending, start=1):
        link = f"https://doi.org/{r['doi']}" if r.get("doi") else "DOI unknown: search by title"
        lines.append(f"| {i} | {r.get('priority')} | {r['record_id']} | {r.get('title', '')[:90]} | {link} |")
        if r["status"] == "NEEDED":
            r["status"] = "MANUAL_REQUESTED"
            r["manual_requested_at"] = now_iso()
            add_attempt(r, "listed for manual browser download")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_ledger(root, ledger)
    print(f"[fulltext] {len(pending)} records listed -> {out}")
    return 0


def pdf_dois(path: Path) -> list[str]:
    found = [canonical_doi(m.group(0)) for m in DOI_RE.finditer(path.stem.replace("_", "/", 1))]
    if shutil.which("pdftotext"):
        try:
            text = subprocess.run(["pdftotext", "-l", "2", str(path), "-"], capture_output=True, text=True,
                                  timeout=60).stdout
            found += [canonical_doi(m.group(0)) for m in DOI_RE.finditer(text)]
        except (subprocess.SubprocessError, OSError):
            pass
    return list(dict.fromkeys(found))


def cmd_import(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ledger = read_csv(root / LEDGER)
    by_doi = {r["doi"]: r for r in ledger if r.get("doi")}
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "intake"))
    import intake  # noqa: E402
    matched, unmatched = 0, []
    for pdf in sorted(Path(args.dir).glob("*.pdf")):
        row = next((by_doi[d] for d in pdf_dois(pdf) if d in by_doi), None)
        if row is None:
            unmatched.append(pdf.name)
            continue
        before = {a["sha256"]: a["attachment_id"] for a in read_csv(root / "inputs/attachments.csv")}
        digest = sha256_file(pdf)
        if digest not in before:
            intake.main(["register", "--root", str(root), "--path", str(pdf), "--kind", "paper",
                         "--purpose", f"full text of {row['record_id']} downloaded by the user", "--access", "INTERNAL"])
        att = next(a for a in read_csv(root / "inputs/attachments.csv") if a["sha256"] == digest)
        row.update(status="AVAILABLE" if row.get("status") != "READ" else "READ",
                   source=f"USER_PROVIDED {att['attachment_id']}", stored_path=att["stored_path"], sha256=digest)
        add_attempt(row, f"user-provided PDF {att['attachment_id']}")
        matched += 1
    write_ledger(root, ledger)
    print(f"[fulltext] matched {matched} PDFs")
    for name in unmatched:
        print(f"[fulltext] no DOI match (identify by hand): {name}")
    return 0


def cmd_mark_read(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ledger = read_csv(root / LEDGER)
    row = next((r for r in ledger if r["record_id"] == args.record_id), None)
    if row is None:
        raise SystemExit(f"[fulltext] unknown record {args.record_id}")
    if row.get("status") not in {"AVAILABLE", "READ"}:
        raise SystemExit(f"[fulltext] {args.record_id} has no obtained full text (status {row.get('status')})")
    row.update(status="READ", location_read=args.location, read_by=args.role)
    write_ledger(root, ledger)
    print(f"[fulltext] {args.record_id} READ ({args.location})")
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ledger = read_csv(root / LEDGER)
    row = next((r for r in ledger if r["record_id"] == args.record_id), None)
    if row is None:
        raise SystemExit(f"[fulltext] unknown record {args.record_id}")
    missing = [step for step, field in (("open-access attempt (fetch-oa)", "oa_attempted_at"),
                                        ("manual request (manual-list)", "manual_requested_at")) if not row.get(field)]
    if missing and row.get("doi"):
        raise SystemExit(f"[fulltext] try first: {', '.join(missing)}")
    row.update(status=args.status, notes="; ".join(filter(None, [row.get("notes", ""), args.note])))
    if args.human_decision:
        row["human_decision"] = args.human_decision
    write_ledger(root, ledger)
    print(f"[fulltext] {args.record_id} -> {args.status}")
    return 0


def audit_fulltext(root: Path, strict: bool, verify_files: bool) -> list[str]:
    issues: list[str] = []
    ledger = read_csv(root / LEDGER)
    by_id = {r["record_id"]: r for r in ledger}
    for r in ledger:
        rid, status = r.get("record_id", "?"), r.get("status", "")
        if status not in STATUSES:
            issues.append(f"{rid}: invalid status {status}")
        if r.get("priority") not in PRIORITIES:
            issues.append(f"{rid}: invalid priority {r.get('priority')}")
        if r.get("need_reason") not in REASONS:
            issues.append(f"{rid}: invalid need_reason {r.get('need_reason')}")
        if status == "READ" and not (r.get("location_read") and r.get("read_by")):
            issues.append(f"{rid}: READ without location_read and read_by")
        if status in {"AVAILABLE", "READ"}:
            if not r.get("stored_path"):
                issues.append(f"{rid}: {status} without stored_path")
            elif verify_files:
                path = root / r["stored_path"]
                if not path.exists():
                    issues.append(f"{rid}: stored full text missing")
                elif r.get("sha256") and sha256_file(path) != r["sha256"]:
                    issues.append(f"{rid}: stored full text modified (hash mismatch)")
            if r.get("stored_path") and not r["stored_path"].startswith((STORE, "inputs/raw/")):
                issues.append(f"{rid}: full text must stay in gitignored {STORE} or inputs/raw/")
        if status in CLOSED_UNREAD and r.get("doi"):
            if not r.get("oa_attempted_at") or not r.get("manual_requested_at"):
                issues.append(f"{rid}: {status} before both an open-access attempt and a manual request")
        if r.get("priority") == "CRITICAL" and status in CLOSED_UNREAD and not r.get("human_decision"):
            issues.append(f"{rid}: CRITICAL paper not read; record a human decision (Decision Log ID) on how to proceed")
        if strict and r.get("priority") == "CRITICAL" and status not in {"READ"} | CLOSED_UNREAD:
            issues.append(f"{rid}: CRITICAL paper full text not yet read ({status})")
        if strict and status in {"NEEDED", "MANUAL_REQUESTED", "AVAILABLE"}:
            issues.append(f"{rid}: full text still {status}")
    for row in read_csv(root / "literature/screening_decisions.csv"):
        if row.get("stage") != "FULL_TEXT":
            continue
        rid = row.get("record_id", "")
        if row.get("exclusion_reason") == "NO_FULL_TEXT" and by_id.get(rid, {}).get("status") != "UNAVAILABLE":
            issues.append(f"{rid}: excluded as NO_FULL_TEXT but the ledger does not show UNAVAILABLE")
        if row.get("decision") in {"INCLUDE", "EXCLUDE"} and row.get("exclusion_reason") != "NO_FULL_TEXT" and \
                by_id.get(rid, {}).get("status") not in {"READ"}:
            issues.append(f"{rid}: full-text decision by {row.get('reviewer')} without a READ full text")
    for row in read_csv(root / "literature/extraction.csv"):
        rid = row.get("record_id", "")
        state = by_id.get(rid, {}).get("status", "")
        if state != "READ" and "ABSTRACT_ONLY" not in row.get("evidence_label", ""):
            issues.append(f"{rid}: extracted without a READ full text; label evidence ABSTRACT_ONLY or read it")
    return issues


def summary(root: Path) -> dict:
    ledger = read_csv(root / LEDGER)
    return {"total": len(ledger), "by_status": dict(Counter(r.get("status") for r in ledger)),
            "critical_not_read": [r["record_id"] for r in ledger
                                  if r.get("priority") == "CRITICAL" and r.get("status") != "READ"]}


def cmd_audit(args: argparse.Namespace) -> int:
    root = Path(args.root)
    issues = audit_fulltext(root, strict=not args.allow_incomplete, verify_files=args.verify_files)
    for issue in issues:
        print(f"[fulltext-audit] {issue}")
    print(f"[fulltext-audit] {json.dumps(summary(root), ensure_ascii=False)}")
    if not issues:
        print("[fulltext-audit] OK")
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".")
    q = sub.add_parser("queue", parents=[common])
    q.add_argument("--record-ids", help="semicolon-separated records to add explicitly")
    q.add_argument("--priority", default="CRITICAL", choices=PRIORITIES)
    q.add_argument("--reason", default="CRITICAL", choices=sorted(REASONS))
    q.add_argument("--no-screening", action="store_true", help="do not add records advanced at title/abstract")
    q.set_defaults(func=cmd_queue)
    f = sub.add_parser("fetch-oa", parents=[common])
    f.set_defaults(func=lambda a: cmd_fetch_oa(a))
    m = sub.add_parser("manual-list", parents=[common])
    m.add_argument("--output", default="results/fulltext/manual_download.md")
    m.set_defaults(func=cmd_manual_list)
    i = sub.add_parser("import", parents=[common])
    i.add_argument("--dir", required=True)
    i.set_defaults(func=cmd_import)
    r = sub.add_parser("mark-read", parents=[common])
    r.add_argument("--record-id", required=True)
    r.add_argument("--location", required=True, help="what was read, e.g. 'Sec. 3-4, Table 2, Fig. 5'")
    r.add_argument("--role", required=True)
    r.set_defaults(func=cmd_mark_read)
    z = sub.add_parser("finalize", parents=[common])
    z.add_argument("--record-id", required=True)
    z.add_argument("--status", required=True, choices=sorted(CLOSED_UNREAD))
    z.add_argument("--note", required=True)
    z.add_argument("--human-decision", help="Decision Log ID; required for CRITICAL records")
    z.set_defaults(func=cmd_finalize)
    a = sub.add_parser("audit", parents=[common])
    a.add_argument("--allow-incomplete", action="store_true")
    a.add_argument("--verify-files", action="store_true")
    a.set_defaults(func=cmd_audit)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
