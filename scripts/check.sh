#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

required_files=(README.md SPECIFICATION.md AGENTS.md AGENTS_CORE.md PROJECT.md STATUS.md LITERATURE.md REFEREE.md paper/main.tex paper/body.tex paper/refs.bib scripts/check.sh .github/workflows/ci.yml literature/SYSTEMATIC_REVIEW_PROTOCOL.md literature/protocol.json literature/journal_scope.json literature/search_log.csv literature/records.csv literature/screening_decisions.csv literature/extraction.csv code/literature/systematic_review.py tests/test_systematic_review.py evidence/analysis_plan.json evidence/runs.csv evidence/checks.csv evidence/claims.csv code/evidence/evidence_audit.py tests/test_evidence_audit.py data/manifest.json code/data/acquire.py code/data/quality.py code/analysis/stats.py code/analysis/record_run.py tests/test_data_analysis.py requirements.txt code/data/discovery.py tests/test_discovery.py literature/gaps.csv data/requirements.csv data/source_search_log.csv data/candidates.csv data/screening_rubric.json CLAUDE.md agents/roles.json code/agents/build_agents.py tests/test_build_agents.py code/data/generate.py tests/test_generated_data.py)
required_dirs=(paper/figures code results tests literature evidence data)

for path in "${required_files[@]}"; do
  [[ -f "$path" ]] || { echo "[check] missing required file: $path" >&2; exit 1; }
done

for path in "${required_dirs[@]}"; do
  [[ -d "$path" ]] || { echo "[check] missing required directory: $path" >&2; exit 1; }
done

for heading in "## PROJECT_STATUS" "## CURRENT_PHASE" "## CURRENT_GATE" "## Current Research Questions" "## Current Findings" "## Claim Evidence Table" "## Current Tasks" "## Blocked Tasks" "## Required Human Input" "## Data Status" "## Implementation Status" "## Verification Status" "## Referee Issues" "## Recent Changes" "## Decision Log" "## Next Actions" "## Final Report Delivery"; do
  grep -Fqx "$heading" STATUS.md || { echo "[check] STATUS.md missing: $heading" >&2; exit 1; }
done

for heading in "## Literature Review Status" "## Systematic Review Protocol" "## Database and Journal Coverage" "## Retrieval and Deduplication Summary" "## Screening and Eligibility" "## Quality Appraisal and Evidence Extraction" "## Citation Chasing and Search Saturation" "## PRISMA Flow" "## Evidence Gap Matrix" "## Journal Search Log" "## Foundational Work" "## Closest Prior Work" "## Recent Primary Studies" "## Systematic Reviews" "## Competing Methods" "## Negative Contradictory Evidence" "## Known Limitations" "## Relevant Standards" "## Cross-disciplinary References" "## Research Gap Synthesis" "## Novelty Assessment" "## Unresolved Literature Questions"; do
  grep -Fqx "$heading" LITERATURE.md || { echo "[check] LITERATURE.md missing: $heading" >&2; exit 1; }
done

for heading in "## Topic Review" "## Scientific and Technical Review" "## Publication Readiness Review" "## Critical Issues" "## Major Issues" "## Minor Issues" "## Falsification Attempts" "## Alternative Explanations" "## Verification Concerns" "## Required Revisions" "## Response to Referee" "## Referee Re-review" "## Resolved Issues" "## Final Referee Decision"; do
  grep -Fqx "$heading" REFEREE.md || { echo "[check] REFEREE.md missing: $heading" >&2; exit 1; }
done

shopt -s nullglob globstar
test_files=()
for path in tests/**/*; do
  [[ -f "$path" && "$(basename "$path")" != ".gitkeep" && "$path" != */__pycache__/* && "$path" != *.pyc ]] && test_files+=("$path")
done

grep -Fq "### Gate 5 — Report Delivery Gate" STATUS.md || { echo "[check] STATUS.md missing Gate 5 delivery checklist" >&2; exit 1; }
grep -Fq '\bibliographystyle{unsrt}' paper/main.tex || { echo "[check] paper/main.tex must use numeric first-citation bibliography style" >&2; exit 1; }
grep -Fq '\input{body}' paper/main.tex || { echo "[check] paper/main.tex must delegate adaptive structure to paper/body.tex" >&2; exit 1; }
grep -Fq 'Citation format: NUMERIC_IN_TEXT' STATUS.md || { echo "[check] numeric in-text citation requirement missing" >&2; exit 1; }
python_bin=""
for candidate in python python3 py; do
  if command -v "$candidate" >/dev/null 2>&1; then python_bin="$candidate"; break; fi
done
if [[ -n "$python_bin" ]]; then
  "$python_bin" code/evidence/evidence_audit.py audit --allow-incomplete --status STATUS.md
  # raw data is gitignored, so CI validates manifest structure only; run without --skip-files where data exists
  "$python_bin" code/data/acquire.py verify --allow-incomplete --skip-files
  "$python_bin" code/data/discovery.py audit --allow-incomplete
  "$python_bin" code/agents/build_agents.py --check
  "$python_bin" code/data/generate.py check-disclosure
else
  echo "[check] Python not found; evidence artifacts were not audited" >&2
fi
if command -v python >/dev/null 2>&1; then
  python code/literature/systematic_review.py audit --allow-incomplete --records literature/records.csv --decisions literature/screening_decisions.csv --journals literature/journal_scope.json --search-log literature/search_log.csv
elif command -v python3 >/dev/null 2>&1; then
  python3 code/literature/systematic_review.py audit --allow-incomplete --records literature/records.csv --decisions literature/screening_decisions.csv --journals literature/journal_scope.json --search-log literature/search_log.csv
elif command -v py >/dev/null 2>&1; then
  py code/literature/systematic_review.py audit --allow-incomplete --records literature/records.csv --decisions literature/screening_decisions.csv --journals literature/journal_scope.json --search-log literature/search_log.csv
else
  echo "[check] Python not found; systematic literature artifacts were not audited" >&2
fi
if (( ${#test_files[@]} > 0 )); then
  if [[ -n "$python_bin" ]] && "$python_bin" -c "import pytest" >/dev/null 2>&1; then
    "$python_bin" -m pytest -q
  elif command -v pytest >/dev/null 2>&1; then
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
