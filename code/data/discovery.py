"""Gap-to-data traceability and data discovery.

Chain audited by this module:

  Problem Definition / RQ (PROJECT.md, Gap IDs column)
    -> research gap (literature/gaps.csv, challenged by a separate role)
      -> data requirement (data/requirements.csv, derived from RQ, gap, analysis plan)
        -> data source search (data/source_search_log.csv, across pathway types)
          -> candidate dataset (data/candidates.csv, scored and screened)
            -> acquired dataset (data/manifest.json) -> quality profile (results/data_quality/)

Commands:
  search   query DataCite or Zenodo for datasets, paginating to exhaustion, and log hits as candidates
  audit    check the chain (``--allow-incomplete`` for work in progress)
  matrix   write results/traceability/chain.json (RQ -> gap -> requirement -> candidate -> data)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

GAP_TYPES = {"EVIDENCE_GAP", "CONTRADICTION_GAP", "METHOD_GAP", "DATA_GAP", "TRANSFER_GAP",
             "IMPLEMENTATION_GAP", "STANDARDIZATION_GAP"}
GAP_DECISIONS = {"NOT_REVIEWED", "ACCEPTED", "NARROWED", "REJECTED"}
EVIDENCE_QUALITY = {"HIGH", "MODERATE", "LOW", "VERY_LOW", "NOT_ASSESSED"}
PRIORITIES = {"MUST", "SHOULD", "COULD"}
REQ_STATUS = {"OPEN", "SEARCHING", "SATISFIED", "PARTIAL", "PROXY", "INSUFFICIENT"}
SOURCE_TYPES = {
    "DATA_REPOSITORY", "DATA_PAPER", "LITERATURE_DATA", "OFFICIAL_STATISTICS", "STANDARD_OR_BENCHMARK",
    "API", "BMS_BEMS_IOT", "BIM_IFC", "MEASUREMENT_PLAN", "SIMULATION", "PROXY", "EXTERNAL_PROVIDER",
    "DESIGN_CHANGE",
}
# DATA_INSUFFICIENT may only be declared after every pathway group was assessed (SPECIFICATION 6).
PATHWAY_GROUPS = {
    "PUBLIC_DATA": {"DATA_REPOSITORY", "DATA_PAPER", "LITERATURE_DATA", "OFFICIAL_STATISTICS", "STANDARD_OR_BENCHMARK"},
    "API": {"API"},
    "MEASUREMENT": {"BMS_BEMS_IOT", "BIM_IFC", "MEASUREMENT_PLAN"},
    "SIMULATION": {"SIMULATION"},
    "PROXY": {"PROXY"},
    "EXTERNAL_PROVIDER": {"EXTERNAL_PROVIDER"},
    "DESIGN_CHANGE": {"DESIGN_CHANGE"},
}
# Minimum discovery before a MUST requirement leaves SEARCHING.
MUST_SOURCE_TYPES = {"DATA_REPOSITORY", "LITERATURE_DATA"}
DECISIONS = {"PENDING", "SELECTED", "BACKUP", "REJECTED", "DUPLICATE"}
SCORES = ["score_fit", "score_coverage", "score_resolution", "score_quality", "score_access",
          "score_cost", "score_reproducibility"]
# A SATISFIED requirement needs a selected candidate at or above these levels; otherwise PARTIAL or PROXY.
SATISFIED_MINIMUM = {"score_fit": 2, "score_coverage": 2, "score_resolution": 2}
RUBRIC_PATH = "data/screening_rubric.json"
CANDIDATE_FIELDS = ["candidate_id", "requirement_ids", "name", "source", "doi_or_url", "search_id",
                    "literature_record_id", "license", "access", "variables_covered", "temporal_resolution",
                    "coverage", "context", "provenance_quality", *SCORES, "score_rationale", "rubric_version",
                    "decision", "decision_reason", "screener_role", "verified_by_role", "duplicate_of", "data_id"]
SEARCH_FIELDS = ["search_id", "search_date", "role", "requirement_ids", "source", "source_type", "query",
                 "filters", "result_count", "retrieved_count", "file_or_url", "access_limitation", "notes"]
USER_AGENT = "research-agent-template/1.0 (data discovery)"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(handle)]


def append_rows(path: Path, fields: list[str], rows: list[dict]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerows(rows)


def ids(value: str) -> list[str]:
    return [v.strip() for v in re.split(r"[;,]", value or "") if v.strip()]


def placeholder(value: str) -> bool:
    return value in ("", "要検討", "TO_DEFINE", "-", "なし")


def parse_rq_table(project_md: Path) -> dict[str, list[str]]:
    """RQ ID -> Gap IDs from the PROJECT.md 'Research Questions' table (placeholder RQs skipped)."""
    if not project_md.exists():
        return {}
    lines = project_md.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## Research Questions")
    except ValueError:
        return {}
    header: list[str] = []
    result: dict[str, list[str]] = {}
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
        if placeholder(row.get("Research Question", "")):
            continue
        result[row.get("RQ ID", "")] = [g for g in ids(row.get("Gap IDs", "")) if not placeholder(g)]
    return result


def load_chain(root: Path) -> dict:
    plan_path = root / "evidence/analysis_plan.json"
    manifest_path = root / "data/manifest.json"
    return {
        "rqs": parse_rq_table(root / "PROJECT.md"),
        "gaps": read_csv(root / "literature/gaps.csv"),
        "extraction": read_csv(root / "literature/extraction.csv"),
        "lit_searches": read_csv(root / "literature/search_log.csv"),
        "lit_records": read_csv(root / "literature/records.csv"),
        "requirements": read_csv(root / "data/requirements.csv"),
        "searches": read_csv(root / "data/source_search_log.csv"),
        "candidates": read_csv(root / "data/candidates.csv"),
        "plan": json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {},
        "manifest": json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {},
        "rubric": json.loads((root / RUBRIC_PATH).read_text(encoding="utf-8")) if (root / RUBRIC_PATH).exists() else {},
        "root": root,
    }


def audit_chain(chain: dict, strict: bool = True) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    rqs = chain["rqs"]
    gaps = {g.get("gap_id", ""): g for g in chain["gaps"]}
    extracted = {r.get("record_id", "") for r in chain["extraction"]}
    lit_search_ids = {s.get("search_id", "") for s in chain["lit_searches"]}
    lit_record_ids = {r.get("record_id", "") for r in chain["lit_records"]}
    analyses = {a.get("analysis_id", ""): a for a in chain["plan"].get("analyses", [])}
    datasets = {d.get("data_id", ""): d for d in chain["manifest"].get("datasets", [])}
    requirements = {r.get("requirement_id", ""): r for r in chain["requirements"]}
    searches = {s.get("search_id", ""): s for s in chain["searches"]}
    candidates = chain["candidates"]

    # Gaps: challenged by another role, grounded in appraised studies and logged searches.
    for gid, gap in gaps.items():
        decision = gap.get("challenger_decision", "")
        if gap.get("gap_type") not in GAP_TYPES:
            issues.append((gid, f"invalid gap_type: {gap.get('gap_type')}"))
        if decision not in GAP_DECISIONS:
            issues.append((gid, f"invalid challenger_decision: {decision}"))
        if gap.get("evidence_quality", "NOT_ASSESSED") not in EVIDENCE_QUALITY:
            issues.append((gid, f"invalid evidence_quality: {gap.get('evidence_quality')}"))
        if decision in {"ACCEPTED", "NARROWED", "REJECTED"}:
            if not gap.get("challenger_role") or gap.get("challenger_role") == gap.get("analyst_role"):
                issues.append((gid, "gap must be challenged by a role other than the Gap Analyst"))
            if not gap.get("challenger_notes"):
                issues.append((gid, "challenger decision has no notes (counter-search, adjacent fields, terms)"))
        if decision in {"ACCEPTED", "NARROWED"}:
            support = ids(gap.get("supporting_record_ids", ""))
            if not support:
                issues.append((gid, "accepted gap cites no supporting studies; absence of hits is not a gap"))
            for rid in support + ids(gap.get("contradicting_record_ids", "")):
                if rid not in extracted:
                    issues.append((gid, f"cited study not quality-appraised/extracted: {rid}"))
            search_ids = ids(gap.get("search_ids", ""))
            if not search_ids:
                issues.append((gid, "accepted gap has no search coverage (search_ids)"))
            for sid in search_ids:
                if sid not in lit_search_ids:
                    issues.append((gid, f"unknown literature search_id: {sid}"))
            if placeholder(gap.get("minimum_closing_design", "")):
                issues.append((gid, "accepted gap has no minimum study design to close it"))

    # RQs must rest on accepted gaps.
    accepted = {gid for gid, g in gaps.items() if g.get("challenger_decision") in {"ACCEPTED", "NARROWED"}}
    for rq, gap_ids in rqs.items():
        for gid in gap_ids:
            if gid not in gaps:
                issues.append((rq, f"RQ references unknown gap: {gid}"))
        if strict and not set(gap_ids) & accepted:
            issues.append((rq, "RQ is not grounded in an ACCEPTED/NARROWED gap"))

    # Requirements: derived from RQ/gap/analysis; status backed by search and data.
    search_types_by_req: dict[str, set[str]] = defaultdict(set)
    for sid, search in searches.items():
        stype = search.get("source_type", "")
        if stype not in SOURCE_TYPES:
            issues.append((sid, f"invalid source_type: {stype}"))
        for rid in ids(search.get("requirement_ids", "")):
            if rid not in requirements:
                issues.append((sid, f"search references unknown requirement: {rid}"))
            search_types_by_req[rid].add(stype)
        try:
            hits = int(search.get("result_count") or 0)
            got = int(search.get("retrieved_count") or 0)
        except ValueError:
            issues.append((sid, "non-integer result_count/retrieved_count"))
            continue
        if got < hits and not search.get("notes"):
            issues.append((sid, f"{hits} hits but {got} retrieved without justification (no result cap)"))

    rubric = chain.get("rubric", {})
    rubric_version = rubric.get("rubric_version", "")
    if rubric:
        criteria = set(rubric.get("criteria", {}))
        if criteria != set(SCORES):
            issues.append(("RUBRIC", f"rubric criteria differ from score columns: {sorted(criteria ^ set(SCORES))}"))
        for name, spec in rubric.get("criteria", {}).items():
            if set(spec.get("levels", {})) != {"0", "1", "2", "3"}:
                issues.append(("RUBRIC", f"{name} must define levels 0-3"))
    must_reqs = {rid for rid, r in requirements.items() if r.get("priority") == "MUST"}
    candidate_ids = {c.get("candidate_id", "") for c in candidates}
    selected_by_req: dict[str, list[dict]] = defaultdict(list)
    for cand in candidates:
        cid = cand.get("candidate_id", "UNKNOWN")
        decision = cand.get("decision", "")
        if decision not in DECISIONS:
            issues.append((cid, f"invalid decision: {decision}"))
        if decision == "DUPLICATE":
            if cand.get("duplicate_of") not in candidate_ids - {cid}:
                issues.append((cid, "DUPLICATE without a valid duplicate_of"))
            continue
        if not (cand.get("search_id") in searches or cand.get("literature_record_id") in lit_record_ids):
            issues.append((cid, "candidate not traceable to a data search or literature record"))
        for rid in ids(cand.get("requirement_ids", "")):
            if rid not in requirements:
                issues.append((cid, f"candidate references unknown requirement: {rid}"))
        if decision != "PENDING":
            if not cand.get("screener_role"):
                issues.append((cid, "screened candidate has no screener_role"))
            for field in SCORES:
                if cand.get(field, "") not in {"0", "1", "2", "3"}:
                    issues.append((cid, f"{field} must be 0-3 once screened"))
            if not cand.get("score_rationale"):
                issues.append((cid, "screened candidate has no score_rationale citing rubric anchors"))
            if rubric_version and cand.get("rubric_version") != rubric_version:
                issues.append((cid, f"scored with rubric {cand.get('rubric_version') or 'none'}, current {rubric_version}"))
        if decision == "REJECTED" and not cand.get("decision_reason"):
            issues.append((cid, "rejected candidate has no decision_reason"))
        if decision == "SELECTED":
            if cand.get("score_fit") == "0" or cand.get("score_access") == "0":
                issues.append((cid, "selected candidate scores 0 on fit or access"))
            if placeholder(cand.get("license", "")) or placeholder(cand.get("access", "")):
                issues.append((cid, "selected candidate has undefined license/access"))
            if set(ids(cand.get("requirement_ids", ""))) & must_reqs:
                verifier = cand.get("verified_by_role", "")
                if not verifier or verifier == cand.get("screener_role"):
                    issues.append((cid, "selection for a MUST requirement needs verified_by_role other than the screener"))
            did = cand.get("data_id", "")
            if did not in datasets:
                issues.append((cid, f"selected candidate has no manifest dataset: {did or 'none'}"))
            for rid in ids(cand.get("requirement_ids", "")):
                selected_by_req[rid].append(cand)
                rq = requirements.get(rid, {}).get("rq_id", "")
                if did in datasets and rq and rq not in datasets[did].get("related_rq", []):
                    issues.append((cid, f"manifest {did} related_rq does not include {rq}"))
        elif strict and decision == "PENDING":
            issues.append((cid, "candidate not screened"))

    for rid, req in requirements.items():
        status, priority = req.get("status", ""), req.get("priority", "")
        if status not in REQ_STATUS:
            issues.append((rid, f"invalid status: {status}"))
        if priority not in PRIORITIES:
            issues.append((rid, f"invalid priority: {priority}"))
        rq = req.get("rq_id", "")
        if rqs and rq not in rqs:
            issues.append((rid, f"requirement references unknown or placeholder RQ: {rq}"))
        if req.get("gap_id") and req["gap_id"] not in gaps:
            issues.append((rid, f"unknown gap_id: {req['gap_id']}"))
        aid = req.get("analysis_id", "")
        if aid and aid not in analyses:
            issues.append((rid, f"unknown analysis_id: {aid}"))
        elif aid and analyses[aid].get("rq_id") not in ("", "TO_DEFINE", rq):
            issues.append((rid, f"analysis {aid} belongs to {analyses[aid].get('rq_id')}, not {rq}"))
        if strict:
            for field in ("required_evidence", "variables", "derivation"):
                if placeholder(req.get(field, "")):
                    issues.append((rid, f"requirement field undefined: {field}"))
        types = search_types_by_req[rid]
        if status in {"SATISFIED", "PARTIAL", "PROXY", "INSUFFICIENT"} and priority == "MUST":
            for stype in sorted(MUST_SOURCE_TYPES - types):
                issues.append((rid, f"MUST requirement decided without a {stype} search"))
        if status in {"SATISFIED", "PARTIAL", "PROXY"}:
            satisfied_by = ids(req.get("satisfied_by", ""))
            if not satisfied_by:
                issues.append((rid, f"{status} without satisfied_by data_id"))
            selected_ids = {c.get("data_id") for c in selected_by_req[rid]}
            if status == "SATISFIED":
                for cand in selected_by_req[rid]:
                    low = [f for f, m in SATISFIED_MINIMUM.items() if cand.get(f, "0").isdigit() and int(cand[f]) < m]
                    if low:
                        issues.append((rid, f"SATISFIED but {cand.get('candidate_id')} scores below 2 on "
                                            f"{', '.join(low)}; use PARTIAL or PROXY"))
            for did in satisfied_by:
                if did not in datasets:
                    issues.append((rid, f"satisfied_by {did} not in data/manifest.json"))
                elif did not in selected_ids:
                    issues.append((rid, f"satisfied_by {did} has no SELECTED candidate for this requirement"))
        if status in {"PARTIAL", "PROXY"} and placeholder(req.get("notes", "")):
            issues.append((rid, f"{status} requires notes on the shortfall or proxy validity"))
        if status == "INSUFFICIENT":
            for group, members in PATHWAY_GROUPS.items():
                if not types & members:
                    issues.append((rid, f"INSUFFICIENT before assessing pathway {group}"))

    # Every dataset in analyses and manifest must be justified by a requirement (no RQ-less collection).
    justified = {did for r in requirements.values() for did in ids(r.get("satisfied_by", ""))}
    if strict:
        for did in datasets:
            if did and did not in justified:
                issues.append((did, "dataset in manifest is not justified by any data requirement"))
        for aid, analysis in analyses.items():
            for did in analysis.get("data_ids", []):
                if did not in justified:
                    issues.append((aid, f"analysis uses {did}, which satisfies no data requirement"))
        for rq in rqs:
            if not any(r.get("rq_id") == rq and r.get("priority") == "MUST" for r in requirements.values()):
                issues.append((rq, "RQ has no MUST data requirement"))
    return issues


def build_matrix(chain: dict) -> dict:
    root: Path = chain["root"]
    gaps = {g.get("gap_id", ""): g for g in chain["gaps"]}
    out: dict = {"generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "rqs": {}}
    rq_ids = set(chain["rqs"]) | {r.get("rq_id", "") for r in chain["requirements"]}
    for rq in sorted(rq_ids):
        reqs = []
        for req in chain["requirements"]:
            if req.get("rq_id") != rq:
                continue
            rid = req.get("requirement_id", "")
            selected = [c for c in chain["candidates"]
                        if rid in ids(c.get("requirement_ids", "")) and c.get("decision") == "SELECTED"]
            data = []
            for did in ids(req.get("satisfied_by", "")):
                report = root / f"results/data_quality/{did}.json"
                quality = json.loads(report.read_text(encoding="utf-8")).get("status") if report.exists() else "NOT_RUN"
                data.append({"data_id": did, "quality": quality})
            reqs.append({
                "requirement_id": rid, "priority": req.get("priority"), "status": req.get("status"),
                "gap_id": req.get("gap_id"), "analysis_id": req.get("analysis_id"),
                "variables": req.get("variables"),
                "source_types_searched": sorted({s.get("source_type") for s in chain["searches"]
                                                 if rid in ids(s.get("requirement_ids", ""))}),
                "candidates_total": sum(rid in ids(c.get("requirement_ids", "")) for c in chain["candidates"]),
                "selected": [c.get("candidate_id") for c in selected],
                "data": data,
            })
        out["rqs"][rq] = {
            "gaps": [{"gap_id": g, "type": gaps.get(g, {}).get("gap_type"),
                      "challenger_decision": gaps.get(g, {}).get("challenger_decision")}
                     for g in chain["rqs"].get(rq, [])],
            "requirements": reqs,
        }
    return out


# ---------------------------------------------------------------- repository search adapters

Fetcher = Callable[[str], dict]


def http_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def search_datacite(query: str, fetch: Fetcher, page_size: int = 100, max_pages: int = 1000):
    """Cursor pagination (page-number pagination is limited to the first 10,000 records)."""
    hits, total, page = [], 0, 1
    params = {"query": query, "resource-type-id": "dataset", "page[size]": page_size, "page[cursor]": 1}
    url = "https://api.datacite.org/dois?" + urllib.parse.urlencode(params)
    while url and page <= max_pages:
        data = fetch(url)
        total = int(data.get("meta", {}).get("total", 0))
        batch = data.get("data", [])
        for item in batch:
            attr = item.get("attributes", {})
            rights = attr.get("rightsList") or [{}]
            hits.append({"name": (attr.get("titles") or [{}])[0].get("title", ""),
                         "source": attr.get("publisher", "") if isinstance(attr.get("publisher"), str)
                         else (attr.get("publisher") or {}).get("name", ""),
                         "doi_or_url": f"https://doi.org/{attr.get('doi')}" if attr.get("doi") else attr.get("url", ""),
                         "license": rights[0].get("rightsIdentifier") or rights[0].get("rights", ""),
                         "coverage": str(attr.get("publicationYear", ""))})
        if not batch or len(hits) >= total:
            break
        url = data.get("links", {}).get("next", "")
        page += 1
    return hits, total


ZENODO_PAGE_SIZE = 25  # anonymous API rejects larger pages
ZENODO_WINDOW = 10_000  # deeper pages are rejected; split the query (e.g. publication_date ranges)


def search_zenodo(query: str, fetch: Fetcher, page_size: int = ZENODO_PAGE_SIZE, max_pages: int = 1000):
    hits, total, page = [], 0, 1
    max_pages = min(max_pages, ZENODO_WINDOW // page_size)
    while page <= max_pages:
        params = {"q": query, "type": "dataset", "size": page_size, "page": page}
        data = fetch("https://zenodo.org/api/records?" + urllib.parse.urlencode(params))
        block = data.get("hits", {})
        total = block.get("total", 0)
        total = int(total.get("value", 0) if isinstance(total, dict) else total)
        batch = block.get("hits", [])
        for item in batch:
            meta = item.get("metadata", {})
            hits.append({"name": meta.get("title", ""), "source": "Zenodo",
                         "doi_or_url": f"https://doi.org/{item['doi']}" if item.get("doi")
                         else item.get("links", {}).get("self_html", ""),
                         "license": (meta.get("license") or {}).get("id", ""),
                         "coverage": meta.get("publication_date", "")})
        if not batch or len(hits) >= total:
            break
        page += 1
    return hits, total


ADAPTERS = {"datacite": search_datacite, "zenodo": search_zenodo}


def doi_key(value: str) -> str:
    match = re.search(r"10\.\d{4,9}/\S+", value or "", flags=re.IGNORECASE)
    return match.group(0).lower().rstrip(".") if match else ""


def run_search(args: argparse.Namespace, fetch: Fetcher = http_json) -> int:
    root = Path(args.root)
    log_path, cand_path = root / "data/source_search_log.csv", root / "data/candidates.csv"
    if any(s.get("search_id") == args.search_id for s in read_csv(log_path)):
        raise SystemExit(f"[discovery] search_id already logged: {args.search_id}")
    hits, total = ADAPTERS[args.source](args.query, fetch, max_pages=args.max_pages)
    raw = root / f"results/data_discovery/{args.search_id}.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps({"query": args.query, "total": total, "hits": hits}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    existing_rows = read_csv(cand_path)
    by_doi = {doi_key(c.get("doi_or_url", "")): c.get("candidate_id", "") for c in existing_rows
              if doi_key(c.get("doi_or_url", "")) and c.get("decision") != "DUPLICATE"}
    rows, duplicates = [], 0
    for i, hit in enumerate(hits, start=1):
        cid = f"DC-{len(existing_rows) + i:05d}"
        row = {**hit, "candidate_id": cid, "requirement_ids": args.requirement_ids,
               "search_id": args.search_id, "decision": "PENDING"}
        key = doi_key(hit.get("doi_or_url", ""))
        if key and key in by_doi:
            row.update(decision="DUPLICATE", duplicate_of=by_doi[key])
            duplicates += 1
        elif key:
            by_doi[key] = cid
        rows.append(row)
    append_rows(cand_path, CANDIDATE_FIELDS, rows)
    append_rows(log_path, SEARCH_FIELDS, [{
        "search_id": args.search_id, "search_date": datetime.now(timezone.utc).date().isoformat(),
        "role": args.role, "requirement_ids": args.requirement_ids, "source": args.source,
        "source_type": "DATA_REPOSITORY", "query": args.query, "filters": "resource type = dataset",
        "result_count": total, "retrieved_count": len(hits), "file_or_url": str(raw.relative_to(root)),
        "notes": "; ".join(filter(None, [
            f"{duplicates} DOI duplicates of earlier candidates" if duplicates else "",
            "" if len(hits) >= total else "API window/page limit reached; split the query (date ranges, terms)",
        ])),
    }])
    print(f"[discovery] {args.source}: {total} hits, {len(hits)} retrieved, {duplicates} duplicates, "
          f"{len(hits) - duplicates} new PENDING candidates")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    issues = audit_chain(load_chain(Path(args.root)), strict=not args.allow_incomplete)
    for scope, message in issues:
        print(f"[discovery-audit] {scope}: {message}")
    return 1 if issues else 0


def cmd_matrix(args: argparse.Namespace) -> int:
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_matrix(load_chain(Path(args.root))), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"[discovery] wrote {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search")
    search.add_argument("--source", choices=sorted(ADAPTERS), required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--search-id", required=True)
    search.add_argument("--requirement-ids", required=True, help="e.g. DR-01;DR-02")
    search.add_argument("--role", default="Data Source Scout")
    search.add_argument("--max-pages", type=int, default=50)
    search.add_argument("--root", default=".")
    search.set_defaults(func=lambda a: run_search(a))
    audit = sub.add_parser("audit")
    audit.add_argument("--root", default=".")
    audit.add_argument("--allow-incomplete", action="store_true")
    audit.set_defaults(func=cmd_audit)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("--root", default=".")
    matrix.add_argument("--output", default="results/traceability/chain.json")
    matrix.set_defaults(func=cmd_matrix)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
