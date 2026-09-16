#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

required_files=(README.md SPECIFICATION.md AGENTS.md AGENTS_CORE.md PROJECT.md STATUS.md LITERATURE.md REFEREE.md paper/main.tex paper/refs.bib scripts/check.sh .github/workflows/ci.yml)
required_dirs=(paper/figures code results tests)

for path in "${required_files[@]}"; do
  [[ -f "$path" ]] || { echo "[check] missing required file: $path" >&2; exit 1; }
done

for path in "${required_dirs[@]}"; do
  [[ -d "$path" ]] || { echo "[check] missing required directory: $path" >&2; exit 1; }
done

for heading in "## PROJECT_STATUS" "## CURRENT_PHASE" "## CURRENT_GATE" "## Current Research Questions" "## Current Findings" "## Claim Evidence Table" "## Current Tasks" "## Blocked Tasks" "## Required Human Input" "## Data Status" "## Implementation Status" "## Verification Status" "## Referee Issues" "## Recent Changes" "## Decision Log" "## Next Actions" "## Final Report Delivery"; do
  grep -Fqx "$heading" STATUS.md || { echo "[check] STATUS.md missing: $heading" >&2; exit 1; }
done

for heading in "## Literature Review Status" "## Foundational Work" "## Closest Prior Work" "## Recent Primary Studies" "## Systematic Reviews" "## Competing Methods" "## Negative Contradictory Evidence" "## Known Limitations" "## Relevant Standards" "## Cross-disciplinary References" "## Research Gap Synthesis" "## Novelty Assessment" "## Unresolved Literature Questions"; do
  grep -Fqx "$heading" LITERATURE.md || { echo "[check] LITERATURE.md missing: $heading" >&2; exit 1; }
done

for heading in "## Topic Review" "## Scientific and Technical Review" "## Publication Readiness Review" "## Critical Issues" "## Major Issues" "## Minor Issues" "## Falsification Attempts" "## Alternative Explanations" "## Verification Concerns" "## Required Revisions" "## Resolved Issues" "## Final Referee Decision"; do
  grep -Fqx "$heading" REFEREE.md || { echo "[check] REFEREE.md missing: $heading" >&2; exit 1; }
done

shopt -s nullglob globstar
test_files=()
for path in tests/**/*; do
  [[ -f "$path" && "$(basename "$path")" != ".gitkeep" && "$path" != */__pycache__/* && "$path" != *.pyc ]] && test_files+=("$path")
done
if (( ${#test_files[@]} > 0 )); then
  if command -v pytest >/dev/null 2>&1; then
    pytest -q
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m unittest discover -s tests -v
  elif command -v python >/dev/null 2>&1; then
    python -m unittest discover -s tests -v
  elif command -v py >/dev/null 2>&1; then
    py -m unittest discover -s tests -v
  else
    echo "[check] Python not found; tests were not executed by this script" >&2
  fi
fi

if command -v latexmk >/dev/null 2>&1; then
  (cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex)
else
  echo "[check] latexmk not found; paper compilation skipped"
fi

echo "[check] OK"
