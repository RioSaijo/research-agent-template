"""Reproducible utilities for systematic literature review artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable


VALID_STAGES = {"TITLE_ABSTRACT", "FULL_TEXT"}
VALID_DECISIONS = {"INCLUDE", "EXCLUDE", "MAYBE", "AWAITING_FULL_TEXT"}
VALID_EXCLUSION_REASONS = {
    "OUT_OF_SCOPE", "WRONG_CONTEXT", "WRONG_OUTCOME", "WRONG_METHOD",
    "WRONG_PUBLICATION_TYPE", "NOT_PEER_REVIEWED", "LANGUAGE", "DATE_RANGE",
    "NO_FULL_TEXT", "DUPLICATE", "RETRACTED", "INSUFFICIENT_REPORTING",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def canonical_doi(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.rstrip(" .")


def normalized_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def mark_duplicates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Mark exact DOI or normalized title/year duplicates; preserve every retrieval row."""
    doi_owner: dict[str, str] = {}
    title_owner: dict[tuple[str, str], str] = {}
    output: list[dict[str, str]] = []
    for index, original in enumerate(rows, start=1):
        row = dict(original)
        record_id = row.get("record_id", "").strip() or f"REC-{index:06d}"
        row["record_id"] = record_id
        row["duplicate_of"] = ""
        doi = canonical_doi(row.get("doi", ""))
        title_key = (normalized_title(row.get("title", "")), row.get("year", "").strip())
        if doi and doi in doi_owner:
            row["duplicate_of"] = doi_owner[doi]
        elif title_key[0] and title_key in title_owner:
            row["duplicate_of"] = title_owner[title_key]
        else:
            if doi:
                doi_owner[doi] = record_id
            if title_key[0]:
                title_owner[title_key] = record_id
        row["doi"] = doi
        output.append(row)
    return output


def stage_outcome(stage: str, decision: str) -> str:
    """Map a reviewer decision to what it means for the record at this stage.

    TITLE_ABSTRACT: EXCLUDE stops the record; INCLUDE, MAYBE and AWAITING_FULL_TEXT all advance it
    to full text. FULL_TEXT: INCLUDE and EXCLUDE are final; MAYBE and AWAITING_FULL_TEXT are pending.
    """
    if stage == "TITLE_ABSTRACT":
        if decision == "EXCLUDE":
            return "EXCLUDE"
        return "ADVANCE" if decision in VALID_DECISIONS else ""
    if decision in {"INCLUDE", "EXCLUDE"}:
        return decision
    return "PENDING" if decision in VALID_DECISIONS else ""


def stage_result(stage: str, rows: list[dict[str, str]]) -> tuple[str, bool]:
    """Return (final outcome or '', conflict flag) for one record at one stage."""
    adjudicated = [r.get("adjudicated_decision", "") for r in rows if r.get("adjudicated_decision", "")]
    if adjudicated:
        return stage_outcome(stage, adjudicated[-1]), False
    outcomes = {stage_outcome(stage, r.get("decision", "")) for r in rows} - {""}
    if not outcomes:
        return "", False
    final_votes = outcomes - {"PENDING"}
    if len(final_votes) > 1:
        return "", True
    if "PENDING" in outcomes:
        return "PENDING", False
    return next(iter(outcomes)), False


def audit_screening(
    records: list[dict[str, str]],
    decisions: list[dict[str, str]],
    require_complete: bool = True,
) -> list[str]:
    issues: list[str] = []
    unique_ids = {r.get("record_id", "") for r in records if not r.get("duplicate_of", "").strip()}
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in decisions:
        record_id, stage = row.get("record_id", ""), row.get("stage", "")
        decision = row.get("decision", "")
        if record_id not in unique_ids:
            issues.append(f"decision references missing or duplicate record: {record_id}")
        if stage not in VALID_STAGES:
            issues.append(f"invalid stage for {record_id}: {stage}")
        if decision not in VALID_DECISIONS:
            issues.append(f"invalid decision for {record_id}: {decision}")
        adjudicated = row.get("adjudicated_decision", "")
        if adjudicated and adjudicated not in VALID_DECISIONS:
            issues.append(f"invalid adjudicated decision for {record_id}: {adjudicated}")
        if adjudicated and not row.get("adjudicator", ""):
            issues.append(f"adjudicated decision without adjudicator: {record_id} at {stage}")
        if decision == "EXCLUDE" and row.get("exclusion_reason", "") not in VALID_EXCLUSION_REASONS:
            issues.append(f"missing/invalid exclusion reason for {record_id} at {stage}")
        grouped[(record_id, stage)].append(row)

    def reviewers(rows: list[dict[str, str]]) -> set[str]:
        return {r.get("reviewer", "") for r in rows if r.get("reviewer", "")}

    for record_id in sorted(unique_ids):
        ta_rows = grouped.get((record_id, "TITLE_ABSTRACT"), [])
        ft_rows = grouped.get((record_id, "FULL_TEXT"), [])
        if require_complete and len(reviewers(ta_rows)) < 2:
            issues.append(f"dual title/abstract screening incomplete: {record_id}")
        ta_final, ta_conflict = stage_result("TITLE_ABSTRACT", ta_rows)
        ft_final, ft_conflict = stage_result("FULL_TEXT", ft_rows)
        if ta_conflict:
            issues.append(f"unresolved screening conflict: {record_id} at TITLE_ABSTRACT")
        if ft_conflict:
            issues.append(f"unresolved screening conflict: {record_id} at FULL_TEXT")
        if ft_rows and ta_final == "EXCLUDE":
            issues.append(f"full-text decision for a record excluded at title/abstract: {record_id}")
        if require_complete and ta_final == "ADVANCE":
            if len(reviewers(ft_rows)) < 2:
                issues.append(f"dual full-text screening incomplete: {record_id}")
            elif ft_final == "PENDING":
                issues.append(f"full-text decision still pending (MAYBE/AWAITING_FULL_TEXT): {record_id}")
    return issues


def prisma_counts(records: list[dict[str, str]], decisions: list[dict[str, str]]) -> dict[str, int]:
    unique_ids = {r.get("record_id", "") for r in records if not r.get("duplicate_of", "").strip()}
    duplicates = sum(bool(r.get("duplicate_of", "").strip()) for r in records)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in decisions:
        grouped[(row.get("record_id", ""), row.get("stage", ""))].append(row)
    ta = {rid: stage_result("TITLE_ABSTRACT", rows) for (rid, stage), rows in grouped.items()
          if stage == "TITLE_ABSTRACT"}
    ft = {rid: stage_result("FULL_TEXT", rows) for (rid, stage), rows in grouped.items() if stage == "FULL_TEXT"}
    return {
        "records_identified": len(records),
        "duplicates_removed": duplicates,
        "unique_records": len(unique_ids),
        "title_abstract_screened": sum(final in {"ADVANCE", "EXCLUDE"} for final, _ in ta.values()),
        "title_abstract_excluded": sum(final == "EXCLUDE" for final, _ in ta.values()),
        "title_abstract_conflicts_unresolved": sum(conflict for _, conflict in ta.values()),
        "full_text_assessed": sum(final in {"INCLUDE", "EXCLUDE"} for final, _ in ft.values()),
        "full_text_excluded": sum(final == "EXCLUDE" for final, _ in ft.values()),
        "full_text_pending": sum(final == "PENDING" for final, _ in ft.values()),
        "full_text_conflicts_unresolved": sum(conflict for _, conflict in ft.values()),
        "studies_included": sum(final == "INCLUDE" for final, _ in ft.values()),
    }


def validate_registry(data: dict) -> list[str]:
    issues: list[str] = []
    if data.get("schema_version") != "1.0.0":
        issues.append("unsupported journal registry schema_version")
    domains = data.get("domains", [])
    if not domains:
        issues.append("journal registry has no domains")
    journals: set[str] = set()
    for domain in domains:
        for journal in domain.get("seed_journals", []):
            key = journal.casefold()
            if key in journals:
                issues.append(f"duplicate seed journal: {journal}")
            journals.add(key)
    if "energy and buildings" not in journals:
        issues.append("required seed journal missing: Energy and Buildings")
    return issues


def audit_search_exports(rows: list[dict[str, str]]) -> list[str]:
    """Detect silent database/UI export caps without imposing a literature cap."""
    issues: list[str] = []
    for row in rows:
        search_id = row.get("search_id", "UNKNOWN")
        raw_hits = row.get("result_count", "").strip()
        raw_exports = row.get("export_count", "").strip()
        if not raw_hits and not raw_exports:
            continue
        try:
            hits, exports = int(raw_hits), int(raw_exports)
        except ValueError:
            issues.append(f"non-integer result/export count: {search_id}")
            continue
        if exports < hits:
            issues.append(
                f"unresolved result/export cap: {search_id} has {hits} hits but {exports} exports"
            )
    return issues


def cmd_dedupe(args: argparse.Namespace) -> int:
    rows = read_csv(Path(args.input))
    marked = mark_duplicates(rows)
    fieldnames = list(rows[0].keys()) if rows else [
        "record_id", "title", "abstract", "authors", "year", "journal", "doi", "url",
        "source_database", "search_id", "retrieved_at", "publication_type", "language",
        "peer_reviewed", "topic_tags", "duplicate_of",
    ]
    if "duplicate_of" not in fieldnames:
        fieldnames.append("duplicate_of")
    write_csv(Path(args.output), marked, fieldnames)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    records = read_csv(Path(args.records))
    decisions = read_csv(Path(args.decisions))
    registry = json.loads(Path(args.journals).read_text(encoding="utf-8"))
    issues = validate_registry(registry) + audit_screening(
        records, decisions, require_complete=not args.allow_incomplete
    )
    if args.search_log:
        issues += audit_search_exports(read_csv(Path(args.search_log)))
    for issue in issues:
        print(f"[literature-audit] {issue}")
    return 1 if issues else 0


def cmd_flow(args: argparse.Namespace) -> int:
    counts = prisma_counts(read_csv(Path(args.records)), read_csv(Path(args.decisions)))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(counts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dedupe = sub.add_parser("dedupe")
    dedupe.add_argument("--input", required=True)
    dedupe.add_argument("--output", required=True)
    dedupe.set_defaults(func=cmd_dedupe)
    audit = sub.add_parser("audit")
    audit.add_argument("--records", required=True)
    audit.add_argument("--decisions", required=True)
    audit.add_argument("--journals", required=True)
    audit.add_argument("--search-log")
    audit.add_argument("--allow-incomplete", action="store_true")
    audit.set_defaults(func=cmd_audit)
    flow = sub.add_parser("flow")
    flow.add_argument("--records", required=True)
    flow.add_argument("--decisions", required=True)
    flow.add_argument("--output", required=True)
    flow.set_defaults(func=cmd_flow)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
