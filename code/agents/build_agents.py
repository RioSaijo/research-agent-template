"""Build platform-specific agent definitions from the single source ``agents/roles.json``.

Outputs (all generated; edit ``agents/roles.json`` instead):

- ``.claude/agents/<id>.md``  Claude Code subagents (YAML frontmatter: name, description, tools)
- ``agents/portable/<id>.md`` platform-neutral instructions for ChatGPT (Projects / custom GPTs),
                              Codex, or any other agent: the same role text without platform syntax
- ``AGENTS.md`` role index between ``<!-- agents:begin -->`` and ``<!-- agents:end -->``

``--check`` fails when a generated file is missing, stale, or orphaned, so CI keeps every
platform on the same role definitions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

CLAUDE_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "Bash", "WebSearch", "WebFetch", "NotebookEdit"}
GATES = {"1", "2", "3", "4", "5"}
BEGIN, END = "<!-- agents:begin -->", "<!-- agents:end -->"
GENERATED = "Generated from agents/roles.json by code/agents/build_agents.py. Do not edit; edit roles.json."


def validate(spec: dict, root: Path) -> list[str]:
    issues: list[str] = []
    if spec.get("schema_version") != "1.0.0":
        issues.append("unsupported roles schema_version")
    roles = spec.get("roles", [])
    ids = [r.get("id", "") for r in roles]
    titles = [r.get("title", "") for r in roles]
    for dup in {i for i in ids if ids.count(i) > 1}:
        issues.append(f"duplicate role id: {dup}")
    for dup in {t for t in titles if titles.count(t) > 1}:
        issues.append(f"duplicate role title: {dup}")
    known = set(ids)
    for role in roles:
        rid = role.get("id", "UNKNOWN")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", rid):
            issues.append(f"{rid}: id must be lowercase kebab-case")
        for field in ("title", "description", "phase"):
            if not role.get(field):
                issues.append(f"{rid}: missing {field}")
        for field in ("reads", "writes", "procedure", "stop"):
            if not role.get(field):
                issues.append(f"{rid}: {field} must not be empty")
        for gate in role.get("gates", []):
            if gate not in GATES:
                issues.append(f"{rid}: invalid gate {gate}")
        for other in role.get("independent_of", []):
            if other not in known:
                issues.append(f"{rid}: independent_of unknown role {other}")
            if other == rid:
                issues.append(f"{rid}: independent_of itself")
        tools = role.get("claude_tools")
        if tools is not None:
            for tool in tools:
                if tool not in CLAUDE_TOOLS:
                    issues.append(f"{rid}: unknown Claude Code tool {tool}")
            if "Write" in tools or "Edit" in tools:
                pass
            elif any(not p.startswith("results/") for p in role.get("writes", [])) and "Bash" not in tools:
                issues.append(f"{rid}: writes repository files but has no Edit/Write/Bash tool")
        for path in role.get("reads", []) + role.get("writes", []):
            if path.endswith("/") or path.startswith("results/"):
                continue
            if not (root / path).exists():
                issues.append(f"{rid}: referenced file does not exist: {path}")
    return issues


def title_of(spec: dict, rid: str) -> str:
    return next((r["title"] for r in spec["roles"] if r["id"] == rid), rid)


def render_body(role: dict, spec: dict) -> str:
    common = spec.get("common", {})
    lines = [f"# {role['title']}", "", role["description"], "",
             f"- Phase: {role['phase']}",
             f"- Quality gates: {', '.join('Gate ' + g for g in role.get('gates', [])) or '-'}",
             f"- Role name to record: `{role['title']}`", "", "## 共通規則", ""]
    lines += [f"- {item}" for item in common.get("preamble", [])]
    lines += ["", "## 入力（読むfile）", ""] + [f"- `{p}`" for p in role["reads"]]
    lines += ["", "## 出力（書いてよいfile）", ""] + [f"- `{p}`" for p in role["writes"]]
    if role.get("independent_of"):
        names = ", ".join(f"{title_of(spec, r)} (`{r}`)" for r in role["independent_of"])
        lines += ["", "## 独立性", "",
                  f"- 次のroleとは別のagent実行・別contextで行う: {names}。",
                  "- 上記roleの判定・採点・結論を、自分の初回判断を記録する前に読まない。",
                  "- 同じagentが上記roleも担当している場合は、このroleを引き受けずResearch Managerへ報告する。"]
    lines += ["", "## 手順", ""] + [f"{i}. {step}" for i, step in enumerate(role["procedure"], start=1)]
    if role.get("must_not"):
        lines += ["", "## してはいけないこと", ""] + [f"- {item}" for item in role["must_not"]]
    lines += ["", "## 停止条件", ""] + [f"- {item}" for item in role["stop"]]
    if role.get("commands"):
        lines += ["", "## 使用するcommand", "", "```bash"] + role["commands"] + ["```"]
    lines += ["", "## 報告", ""] + [f"- {item}" for item in common.get("output_contract", [])]
    return "\n".join(lines) + "\n"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_claude(role: dict, spec: dict) -> str:
    front = ["---", f"name: {role['id']}", f"description: {yaml_string(role['description'])}"]
    if role.get("claude_tools") is not None:
        front.append(f"tools: {', '.join(role['claude_tools'])}")
    front += ["---", "", f"<!-- {GENERATED} -->", ""]
    return "\n".join(front) + render_body(role, spec)


def render_portable(role: dict, spec: dict) -> str:
    header = [f"<!-- {GENERATED} -->", "",
              "> Platform-neutral role instructions. ChatGPT: paste into a Project or custom GPT instruction, "
              "or ask it to read this file from the repository. Codex / other agents: read this file and act only as this role. "
              "Claude Code: use the subagent of the same name in `.claude/agents/`.", ""]
    return "\n".join(header) + render_body(role, spec)


def render_index(spec: dict) -> str:
    lines = [BEGIN, "", "## Expert agent roles", "",
             f"<!-- {GENERATED} -->", "",
             "role定義の正本は`agents/roles.json`。同じ定義から各platform用fileを生成するため、どのplatformでも同じroleを使える。",
             "",
             "- Claude Code: `.claude/agents/<id>.md`のsubagentとして起動する（例: 「data-screener agentでDR-01の候補を採点」）。",
             "- ChatGPT: `agents/portable/<id>.md`をProject/custom GPTの指示として使うか、repositoryから読ませる。",
             "- Codex / その他: `agents/portable/<id>.md`を読み、そのroleだけを実行する。",
             "- 独立性が必要なrole（独立性欄）は、platformを問わず別のagent実行・別contextで起動する。",
             "",
             "| Role | Gate | Independent of | Claude Code | Portable |",
             "|---|---|---|---|---|"]
    for role in spec["roles"]:
        rid = role["id"]
        lines.append(f"| {role['title']} | {', '.join(role.get('gates', []))} | "
                     f"{', '.join(role.get('independent_of', [])) or '-'} | "
                     f"`.claude/agents/{rid}.md` | `agents/portable/{rid}.md` |")
    lines += ["", END]
    return "\n".join(lines)


def expected_files(spec: dict, root: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for role in spec["roles"]:
        files[root / ".claude/agents" / f"{role['id']}.md"] = render_claude(role, spec)
        files[root / "agents/portable" / f"{role['id']}.md"] = render_portable(role, spec)
    agents_md = root / "AGENTS.md"
    current = agents_md.read_text(encoding="utf-8") if agents_md.exists() else ""
    index = render_index(spec)
    if BEGIN in current and END in current:
        new = current[:current.index(BEGIN)] + index + current[current.index(END) + len(END):]
    else:
        new = current.rstrip("\n") + "\n\n" + index + "\n"
    files[agents_md] = new
    return files


def orphans(spec: dict, root: Path) -> list[Path]:
    wanted = {r["id"] for r in spec["roles"]}
    found = []
    for folder in (root / ".claude/agents", root / "agents/portable"):
        if folder.exists():
            found += [p for p in folder.glob("*.md") if p.stem not in wanted]
    return found


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true", help="fail if generated files are missing or stale")
    args = parser.parse_args(argv)
    root = Path(args.root)
    spec = json.loads((root / "agents/roles.json").read_text(encoding="utf-8"))
    issues = validate(spec, root)
    if issues:
        for issue in issues:
            print(f"[agents] {issue}", file=sys.stderr)
        return 1
    files = expected_files(spec, root)
    if args.check:
        stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        stale += orphans(spec, root)
        for path in stale:
            print(f"[agents] out of date or orphaned: {path.relative_to(root)}", file=sys.stderr)
        if stale:
            print("[agents] run: python code/agents/build_agents.py", file=sys.stderr)
        return 1 if stale else 0
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for path in orphans(spec, root):
        path.unlink()
    print(f"[agents] generated {len(spec['roles'])} roles for Claude Code and portable use")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
