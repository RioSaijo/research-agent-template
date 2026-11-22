---
name: research-manager
description: "Use when starting or continuing a research project in this repository, checking its status, choosing the next research task, or coordinating the defined research roles."
---

# Research Manager Skill

Use this skill to enter and coordinate the research workflow in this repository. The repository's instructions and recorded state remain authoritative.

## Start here

1. Read `AGENTS.md` and `AGENTS_CORE.md`.
2. Read `PROJECT.md` and `STATUS.md`.
3. Identify the current research stage, gate, phase, highest-priority executable task, and any blocking human decision.
4. Read only the protocol, role definition, and evidence files needed for that task.

## Coordinate work

- Follow the workflow and human decision points in `AGENTS.md` and `SPECIFICATION.md`.
- Select roles from `agents/roles.json`. Use generated role files under `agents/portable/` or `.claude/agents/`; do not edit generated role files directly.
- Start independent reviews in separate agent executions and contexts. If the current platform cannot do that, report the limitation and leave the review pending. Do not simulate independence by changing role labels in one context.
- Use repository scripts for deterministic operations when a shell is available. Inspect each command and its expected inputs before running it.
- If a required connector, repository permission, shell, or agent capability is unavailable, record what could not be done and continue with work that does not depend on it.

## Preserve evidence and state

- Treat repository records as the source of truth over chat history.
- Do not invent sources, numerical results, verification, or completed actions. Distinguish verified findings from interpretation and unresolved items.
- Update the existing authoritative files and machine-readable records specified for the task. Do not create parallel status records.
- Report changed files, commands actually run, their actual results, unresolved issues, and the next task.
- Never report a search, test, file edit, commit, or external action as completed unless it was actually completed in the current environment.

## Platform limits

This skill does not grant repository access, shell execution, external connectors, or subagents. Confirm which capabilities are available in the current ChatGPT, Codex, or Claude session. In ChatGPT, the package may need to be installed or uploaded where Skills are supported. A repository connection alone does not imply write access or command execution.
