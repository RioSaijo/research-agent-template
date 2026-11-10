import copy
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("build_agents", ROOT / "code/agents/build_agents.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
ROLES = json.loads((ROOT / "agents/roles.json").read_text(encoding="utf-8"))


def test_repository_roles_are_valid_and_generated_files_in_sync():
    assert MODULE.validate(ROLES, ROOT) == []
    assert MODULE.main(["--root", str(ROOT), "--check"]) == 0


def test_every_role_exists_on_every_platform():
    for role in ROLES["roles"]:
        claude = (ROOT / ".claude/agents" / f"{role['id']}.md").read_text(encoding="utf-8")
        portable = (ROOT / "agents/portable" / f"{role['id']}.md").read_text(encoding="utf-8")
        assert claude.startswith(f"---\nname: {role['id']}\n")
        assert MODULE.render_body(role, ROLES) in claude
        assert MODULE.render_body(role, ROLES) in portable
        assert "name:" not in portable.split("\n", 1)[0]


def test_role_names_match_audit_role_conventions():
    titles = {r["title"] for r in ROLES["roles"]}
    for needed in ("Analyst", "Methods Challenger", "Independent Verifier", "Screener A", "Screener B",
                   "Gap Analyst", "Gap Challenger", "Data Screener", "Data Verifier", "Referee", "Revision Lead"):
        assert needed in titles


def test_independent_pairs_are_declared_both_ways_for_critical_roles():
    by_id = {r["id"]: set(r["independent_of"]) for r in ROLES["roles"]}
    for a, b in [("screener-a", "screener-b"), ("gap-analyst", "gap-challenger"),
                 ("data-screener", "data-verifier"), ("referee", "revision-lead"),
                 ("search-strategist", "search-peer-reviewer"), ("analyst", "methods-challenger")]:
        assert b in by_id[a] and a in by_id[b], (a, b)


def test_validation_catches_unknown_references_and_tools():
    bad = copy.deepcopy(ROLES)
    bad["roles"][0]["independent_of"] = ["no-such-role"]
    bad["roles"][1]["claude_tools"] = ["Teleport"]
    issues = MODULE.validate(bad, ROOT)
    assert any("unknown role no-such-role" in i for i in issues)
    assert any("unknown Claude Code tool Teleport" in i for i in issues)


def test_check_detects_stale_and_orphaned_files(tmp_path):
    for rel in ("agents/roles.json", "AGENTS.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    spec = json.loads((tmp_path / "agents/roles.json").read_text(encoding="utf-8"))
    for role in spec["roles"]:
        role["reads"] = ["AGENTS.md"]
        role["writes"] = ["AGENTS.md"]
    (tmp_path / "agents/roles.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    assert MODULE.main(["--root", str(tmp_path)]) == 0
    assert MODULE.main(["--root", str(tmp_path), "--check"]) == 0
    target = tmp_path / ".claude/agents/referee.md"
    target.write_text(target.read_text(encoding="utf-8") + "manual edit\n", encoding="utf-8")
    assert MODULE.main(["--root", str(tmp_path), "--check"]) == 1
    assert MODULE.main(["--root", str(tmp_path)]) == 0
    (tmp_path / "agents/portable/old-role.md").write_text("x", encoding="utf-8")
    assert MODULE.main(["--root", str(tmp_path), "--check"]) == 1
