# CLAUDE.md

Claude Codeの入口。研究運用の規則はplatform共通の`AGENTS.md`を正本とし、ここでは複製しない。

@AGENTS.md

- Expert roleは`.claude/agents/`のsubagentとして起動する。これらは`agents/roles.json`から生成されたfileであり、直接編集しない。role定義を変える場合は`agents/roles.json`を編集し`python code/agents/build_agents.py`を実行する。
- 独立性が必要なrole（`AGENTS.md`のIndependent of列）は、別のsubagent呼び出しで実行し、同じcontextで続けて担当しない。
