"""Verify bibliographic references against Crossref and OpenAlex.

Check statuses, strongest first:
  ORIGINAL_CHECKED     a role read the original (publisher page, author manuscript, PDF); set by hand
                       with the location read, never by this script
  METADATA_VERIFIED    the DOI resolves and title (and year, when given) match the registry record
  SEARCH_SUMMARY_ONLY  known only from a search-engine snippet or summary; not evidence
  MISMATCH             the DOI resolves to a different work, or the year differs
  NOT_FOUND            the DOI is not registered

Commands:
  doi      verify one DOI against an expected title/year
  find     look up DOI candidates for a title without one
  bib      verify every entry of a BibTeX file (Gate 4 reference check)
  options  verify the supporting sources of exploration options in inputs/intake.json
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

USER_AGENT = "research-agent-template/1.0 (reference verification)"
STRONG = {"ORIGINAL_CHECKED", "METADATA_VERIFIED"}
STATUSES = STRONG | {"SEARCH_SUMMARY_ONLY", "MISMATCH", "NOT_FOUND"}
TITLE_MATCH = 0.8          # Jaccard similarity that counts as the same title
CONTAINMENT_MATCH = 0.9    # or: expected title (e.g. without subtitle) contained in the registry title...
CONTAINMENT_FLOOR = 0.5    # ...while still sharing at least half of all words
Fetcher = Callable[[str], dict | None]


def http_json(url: str) -> dict | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def canonical_doi(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.rstrip(" .")


def tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFKD", text or "").casefold()
    return set(re.findall(r"[a-z0-9]+", text)) - {"a", "an", "the", "of", "and", "in", "for", "on", "to", "with"}


def title_similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def titles_match(expected: str, registered: str) -> tuple[bool, float, float]:
    te, tr = tokens(expected), tokens(registered)
    if not te or not tr:
        return False, 0.0, 0.0
    jaccard = len(te & tr) / len(te | tr)
    containment = len(te & tr) / len(te)
    return (jaccard >= TITLE_MATCH or (containment >= CONTAINMENT_MATCH and jaccard >= CONTAINMENT_FLOOR)), jaccard, containment


def abstract_from_inverted(index: dict | None) -> str:
    if not index:
        return ""
    positions = sorted((pos, word) for word, places in index.items() for pos in places)
    return " ".join(word for _, word in positions)


def lookup(doi: str, fetch: Fetcher = http_json) -> dict | None:
    """Registry record for a DOI: Crossref first, OpenAlex for abstract / open-access link or as fallback."""
    record = None
    crossref = fetch("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if crossref and crossref.get("message"):
        m = crossref["message"]
        parts = (m.get("issued") or m.get("published") or {}).get("date-parts") or [[None]]
        record = {
            "registry": "Crossref", "doi": canonical_doi(m.get("DOI", doi)),
            "title": (m.get("title") or [""])[0],
            "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in m.get("author", [])],
            "year": parts[0][0], "container": (m.get("container-title") or [""])[0],
            "volume": m.get("volume", ""), "issue": m.get("issue", ""),
            "pages": m.get("page", "") or m.get("article-number", ""), "type": m.get("type", ""),
        }
    openalex = fetch("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
    if openalex:
        location = (openalex.get("primary_location") or {}).get("source") or {}
        extra = {"abstract": abstract_from_inverted(openalex.get("abstract_inverted_index")),
                 "open_access_url": (openalex.get("open_access") or {}).get("oa_url") or "",
                 "openalex_id": openalex.get("id", "")}
        if record is None:
            record = {"registry": "OpenAlex", "doi": canonical_doi(openalex.get("doi", doi)),
                      "title": openalex.get("title", ""), "year": openalex.get("publication_year"),
                      "authors": [a.get("author", {}).get("display_name", "") for a in openalex.get("authorships", [])],
                      "container": location.get("display_name", ""), "volume": "", "issue": "", "pages": "",
                      "type": openalex.get("type", "")}
        record.update(extra)
    return record


def verify(doi: str, expected_title: str = "", expected_year: str | int = "", fetch: Fetcher = http_json) -> dict:
    doi = canonical_doi(doi)
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if not doi:
        return {"doi": "", "status": "SEARCH_SUMMARY_ONLY", "reason": "no DOI to verify", "checked_at": checked}
    record = lookup(doi, fetch)
    if record is None:
        return {"doi": doi, "status": "NOT_FOUND", "reason": "DOI not registered in Crossref or OpenAlex",
                "checked_at": checked}
    reasons = []
    similarity = None
    if expected_title:
        matched, similarity, containment = titles_match(expected_title, record["title"])
        if not matched:
            reasons.append(f"title does not match the registry (similarity {similarity:.2f}, containment {containment:.2f})")
    if expected_year and record.get("year") and str(expected_year)[:4] != str(record["year"]):
        reasons.append(f"year {expected_year} differs from registry {record['year']}")
    status = "MISMATCH" if reasons else "METADATA_VERIFIED"
    return {"doi": doi, "status": status, "reason": "; ".join(reasons), "title_similarity": similarity,
            "record": record, "checked_at": checked}


def find(title: str, rows: int = 5, fetch: Fetcher = http_json) -> list[dict]:
    query = urllib.parse.urlencode({"query.bibliographic": title, "rows": rows})
    data = fetch("https://api.crossref.org/works?" + query) or {}
    out = []
    for item in data.get("message", {}).get("items", []):
        candidate = (item.get("title") or [""])[0]
        out.append({"doi": canonical_doi(item.get("DOI", "")), "title": candidate,
                    "year": ((item.get("issued") or {}).get("date-parts") or [[None]])[0][0],
                    "container": (item.get("container-title") or [""])[0],
                    "title_similarity": round(title_similarity(title, candidate), 3)})
    return sorted(out, key=lambda c: -c["title_similarity"])


def parse_bib(text: str) -> list[dict[str, str]]:
    entries = []
    for block in re.split(r"(?=@\w+\s*\{)", text):
        head = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", block)
        if not head or head.group(1).lower() in {"comment", "string", "preamble"}:
            continue
        entry = {"key": head.group(2)}
        for field in ("title", "year", "doi", "journal", "author"):
            match = re.search(rf"\b{field}\s*=\s*[{{\"](.+?)[}}\"]\s*,?\s*\n", block, re.IGNORECASE | re.DOTALL)
            if match:
                entry[field] = re.sub(r"[{}\s]+", " ", match.group(1)).strip()
        entries.append(entry)
    return entries


def verify_bib(text: str, fetch: Fetcher = http_json) -> list[dict]:
    results = []
    for entry in parse_bib(text):
        if not entry.get("doi"):
            results.append({"key": entry["key"], "status": "SEARCH_SUMMARY_ONLY",
                            "reason": "no DOI; verify the original by hand and record ORIGINAL_CHECKED, or add a DOI",
                            "candidates": find(entry.get("title", ""), 3, fetch) if entry.get("title") else []})
            continue
        result = verify(entry["doi"], entry.get("title", ""), entry.get("year", ""), fetch)
        results.append({"key": entry["key"], **result})
    return results


def option_issues(options: list[dict], minimum: int = 2) -> list[str]:
    issues = []
    for option in options:
        oid = option.get("option_id", "?")
        sources = option.get("supporting_sources", [])
        if any(not isinstance(s, dict) for s in sources):
            issues.append(f"{oid}: supporting_sources must be objects with citation, doi, check_status")
            continue
        strong = [s for s in sources if s.get("check_status") in STRONG]
        if len(strong) < minimum:
            issues.append(f"{oid}: {len(strong)} verified supporting source(s); needs {minimum} with "
                          "ORIGINAL_CHECKED or METADATA_VERIFIED")
        for s in sources:
            if s.get("check_status") not in STATUSES:
                issues.append(f"{oid}: invalid check_status {s.get('check_status')} for {s.get('citation', '?')}")
            if s.get("check_status") == "ORIGINAL_CHECKED" and not s.get("location_read"):
                issues.append(f"{oid}: ORIGINAL_CHECKED needs location_read for {s.get('citation', '?')}")
    return issues


def cmd_doi(args: argparse.Namespace) -> int:
    result = verify(args.doi, args.title or "", args.year or "")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "METADATA_VERIFIED" else 1


def cmd_find(args: argparse.Namespace) -> int:
    print(json.dumps(find(args.title, args.rows), ensure_ascii=False, indent=2))
    return 0


def cmd_bib(args: argparse.Namespace) -> int:
    results = verify_bib(Path(args.bib).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bad = [r for r in results if r["status"] not in STRONG]
    for r in results:
        print(f"[verify-refs] {r['key']}: {r['status']} {r.get('reason', '')}".rstrip())
    print(f"[verify-refs] {len(results) - len(bad)}/{len(results)} verified -> {output}")
    return 1 if bad else 0


def cmd_options(args: argparse.Namespace) -> int:
    path = Path(args.intake)
    intake = json.loads(path.read_text(encoding="utf-8"))
    for option in intake.get("exploration", {}).get("options", []):
        for source in option.get("supporting_sources", []):
            if not isinstance(source, dict) or source.get("check_status") == "ORIGINAL_CHECKED":
                continue
            result = verify(source.get("doi", ""), source.get("title", ""), source.get("year", ""))
            source["check_status"] = result["status"]
            source["checked_at"] = result["checked_at"]
            if result.get("record"):
                rec = result["record"]
                source["verified_citation"] = (f"{', '.join(rec['authors'][:3])}{' et al.' if len(rec['authors']) > 3 else ''}"
                                               f" ({rec['year']}). {rec['title']}. {rec['container']}"
                                               f"{' ' + str(rec['volume']) if rec['volume'] else ''}"
                                               f"{', ' + str(rec['pages']) if rec['pages'] else ''}. doi:{rec['doi']}")
                source["open_access_url"] = rec.get("open_access_url", "")
            if result.get("reason"):
                source["check_reason"] = result["reason"]
    path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    issues = option_issues(intake.get("exploration", {}).get("options", []))
    for issue in issues:
        print(f"[verify-refs] {issue}")
    print("[verify-refs] options ready to present" if not issues else "[verify-refs] options not ready")
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doi")
    d.add_argument("--doi", required=True)
    d.add_argument("--title")
    d.add_argument("--year")
    d.set_defaults(func=cmd_doi)
    f = sub.add_parser("find")
    f.add_argument("--title", required=True)
    f.add_argument("--rows", type=int, default=5)
    f.set_defaults(func=cmd_find)
    b = sub.add_parser("bib")
    b.add_argument("--bib", default="paper/refs.bib")
    b.add_argument("--output", default="results/references/verification.json")
    b.set_defaults(func=cmd_bib)
    o = sub.add_parser("options")
    o.add_argument("--intake", default="inputs/intake.json")
    o.set_defaults(func=cmd_options)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
