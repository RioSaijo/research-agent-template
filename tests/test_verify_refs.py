import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("verify_refs", ROOT / "code/literature/verify_refs.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

CROSSREF = {"message": {"DOI": "10.1016/j.enbuild.2023.113801",
                        "title": ["Barriers and drivers for implementation of automatic fault detection and diagnosis "
                                  "in buildings and HVAC systems: An outlook from industry experts"],
                        "author": [{"given": "K.", "family": "Andersen"}], "issued": {"date-parts": [[2024, 1]]},
                        "container-title": ["Energy and Buildings"], "volume": "303", "article-number": "113801"}}
OPENALEX = {"id": "W1", "abstract_inverted_index": {"Barriers": [0], "matter": [1]},
            "open_access": {"oa_url": "https://example.org/oa.pdf"}}


def fake(url):
    if "api.crossref.org/works/10.1016" in url:
        return CROSSREF
    if "api.openalex.org/works/doi:10.1016" in url:
        return OPENALEX
    return None


def test_title_without_subtitle_is_verified():
    r = MODULE.verify("https://doi.org/10.1016/J.ENBUILD.2023.113801",
                      "Barriers and drivers for implementation of automatic fault detection and diagnosis in buildings "
                      "and HVAC systems", 2024, fetch=fake)
    assert r["status"] == "METADATA_VERIFIED"
    assert r["record"]["abstract"] == "Barriers matter" and r["record"]["open_access_url"]


def test_wrong_title_or_year_is_mismatch_and_unknown_doi_not_found():
    assert MODULE.verify("10.1016/j.enbuild.2023.113801", "A review of fault detection methods", 2024,
                         fetch=fake)["status"] == "MISMATCH"
    assert MODULE.verify("10.1016/j.enbuild.2023.113801", "", 2019, fetch=fake)["status"] == "MISMATCH"
    assert MODULE.verify("10.9999/none", "x", 2020, fetch=fake)["status"] == "NOT_FOUND"
    assert MODULE.verify("", "x", 2020, fetch=fake)["status"] == "SEARCH_SUMMARY_ONLY"


def test_bib_entries_without_doi_are_not_verified():
    bib = ("@article{andersen2024,\n  title = {Barriers and drivers for implementation of automatic fault detection "
           "and diagnosis in buildings and HVAC systems},\n  year = {2024},\n  doi = {10.1016/j.enbuild.2023.113801},\n}\n"
           "@inproceedings{house2001,\n  title = {An expert rule set for fault detection},\n  year = {2001},\n}\n")
    results = {r["key"]: r["status"] for r in MODULE.verify_bib(bib, fetch=fake)}
    assert results == {"andersen2024": "METADATA_VERIFIED", "house2001": "SEARCH_SUMMARY_ONLY"}


def test_options_need_two_verified_sources():
    options = [{"option_id": "OPT-1", "supporting_sources": [
        {"citation": "a", "check_status": "METADATA_VERIFIED"},
        {"citation": "b", "check_status": "SEARCH_SUMMARY_ONLY"}]},
        {"option_id": "OPT-2", "supporting_sources": ["plain string"]},
        {"option_id": "OPT-3", "supporting_sources": [
            {"citation": "c", "check_status": "ORIGINAL_CHECKED"},
            {"citation": "d", "check_status": "METADATA_VERIFIED"}]}]
    issues = MODULE.option_issues(options)
    assert any("OPT-1: 1 verified" in i for i in issues)
    assert any("OPT-2: supporting_sources must be objects" in i for i in issues)
    assert any("OPT-3: ORIGINAL_CHECKED needs location_read" in i for i in issues)
