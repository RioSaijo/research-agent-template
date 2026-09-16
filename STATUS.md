# STATUS

## PROJECT_STATUS

`ACTIVE`

## CURRENT_PHASE

`Data Requirement`

## CURRENT_GATE

`Gate 2 — Methodology Readiness Gate`

## Current Research Questions

| RQ ID | Summary | Status | Critical Issue |
|---|---|---|---|
| RQ-01 | Semantic contextはunseen-building IEQ predictionを改善するか | READY_FOR_DATA | matched timeseries+semantic graph未取得 |
| RQ-02 | Semantic assemblyはsetup effortを削減できるか | READY_FOR_DATA | mapping study未実施 |

## Current Findings

- `[LITERATURE]` Semantic IEQ integrationとpersonal comfort modelingは既に存在し、「初適用」は主張できない。
- `[LITERATURE]` portable analyticsはBrick/Mortarで実証例があるが、accuracy improvementとは別のclaimである。
- `[SOFTWARE_TEST]` sensor→room→zone context assemblyとmissing mapping coverageの最小実装を作成した。
- `[OPEN]` predictive performance improvementはdataがないため未検証。

## Claim Evidence Table

| Claim ID | RQ | Claim | Evidence Type | Primary Evidence | Independent Check | Verification | Claim Status | Referee |
|---|---|---|---|---|---|---|---|---|
| CL-01 | RQ-01 | semantic contextがbuilding-held-out MAEを10%以上改善する | EXPERIMENT | なし | edge ablation/model replication予定 | NOT_VERIFIED | OPEN | NOT_READY |
| CL-02 | RQ-02 | semantic assemblyがsetup timeを30%以上削減しrecall 0.95以上を保つ | EXPERIMENT | なし | second annotator/SHACL予定 | NOT_VERIFIED | OPEN | NOT_READY |
| CL-03 | RQ-02 | explicit graph relationからfeature contextを再現可能に組み立てられる | SOFTWARE_TEST | code/integration/semantic_ieq_features.py; tests | local unit tests | INTERNALLY_VERIFIED | PRELIMINARY | ACCEPTABLE_AS_SCAFFOLD |

## Current Tasks

| Task ID | Related RQ | Task | Purpose | Owner / Role | Dependency | Required Resource | Output | Status | Priority | Blocking Issue | Related Quality Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | ALL | initial literature reviewとgap定義 | novelty/readiness | Literature | Theme | Web/primary sources | LITERATURE.md | DONE | P0 | None | Gate 1 |
| T-002 | ALL | RQ mappingとevaluation criterion | verifiability | Manager/Methodology | T-001 | Literature | PROJECT.md | DONE | P0 | None | Gate 2 |
| T-003 | RQ-02 | semantic feature scaffoldとtests | executable protocol | Software Architecture | T-002 | Repository | code/tests | DONE | P1 | None | Gate 2 |
| T-004 | RQ-01 | matched multi-building dataset確保 | empirical evidence | Data Requirement | T-002 | Public/project data | provenance record | BLOCKED | P0 | no matched data | Gate 2 |
| T-005 | RQ-01 | three-condition building-held-out experiment | primary evidence | Analysis | T-004 | Data | results | BLOCKED | P0 | T-004 | Gate 3 |
| T-006 | RQ-02 | counterbalanced mapping study | portability evidence | Verification | T-004 | buildings/annotators | results | BLOCKED | P1 | T-004 | Gate 3 |

## Blocked Tasks

| Task ID | Blocker | Resolution Path | Human Required |
|---|---|---|---|
| T-004 | timeseriesとsemantic graphが対応する複数building dataなし | public resource feasibility review、またはproject data提供 | POSSIBLY |
| T-005 | T-004 | acquire/validate data | NO after data access |
| T-006 | building modelsとannotator未確保 | reference modelsでpilot後、independent annotator | YES for final study |

## Required Human Input

| Input ID | Reason | Decision Needed | Effect if Deferred | Status |
|---|---|---|---|---|
| H-001 | final targetはavailable dataに依存 | CO₂ / thermal comfort vote / overall IEQ satisfaction | protocol remains target-agnostic; experiment cannot start | REQUIRED_FOR_EMPIRICAL_PHASE |
| H-002 | project BMS/IoT dataがある場合 | access authorizationとdata dictionary | public-data route only | OPTIONAL |

## Data Status

- Required data: multi-building IEQ timeseries + semantic graph + target ground truth。
- Available data: publications/reference models only。
- Acquisition feasibility: plausible but matched public package not yet verified。
- Provenance status: DESIGN_COMPLETE / DATA_NOT_ACQUIRED。
- Data quality status: CHECKLIST_DEFINED / NOT_RUN。

## Implementation Status

- Full implementation readiness: BLOCKED_BY_DATA。
- Semantic feature scaffold: IMPLEMENTED。
- Reproducibility checks: UNIT_TESTED。

## Verification Status

- Evaluation Criterion defined: YES。
- Primary Evidence exists: NO。
- Criterion applied: NO。
- Alternative explanations: IDENTIFIED, NOT_TESTED。
- Independent verification plan: DEFINED。
- Verification state: NOT_VERIFIED。

## Referee Issues

| Issue ID | Stage | Severity | Related RQ / Claim | Issue | Required Revision | Status | Task ID |
|---|---|---|---|---|---|---|---|
| RF-001 | Topic | MAJOR | RQ-01 | target variable未固定 | data feasibility後にtarget固定 | OPEN | T-004 |
| RF-002 | Scientific | CRITICAL | CL-01, CL-02 | empirical evidenceなし | matched dataでpredefined experiment | OPEN | T-005/T-006 |
| RF-003 | Topic | MAJOR | Novelty | equivalent ablation見落としの可能性 | citation-chain/database search | OPEN | new task after data feasibility |

## Quality Gates

### Gate 1 — Research Definition Gate

- [x] Background defined
- [x] Motivation defined
- [x] Problem Definition supported by literature
- [x] RQ defined
- [x] Closest Prior Work identified
- [x] Research Gap defined
- [x] Scope reasonable

### Gate 2 — Methodology Readiness Gate

- [x] RQ Data Method mapping complete
- [x] Required Data identified
- [ ] Reasonable acquisition path verified
- [x] Evaluation Metric defined
- [x] Evaluation Criterion defined
- [x] Baseline / Reference defined
- [x] Verification Plan defined

### Gate 3 — Evidence and Verification Gate

- [ ] Primary Evidence exists
- [ ] Evidence provenance traceable
- [ ] Evaluation Criterion applied
- [x] Claim Status assigned
- [ ] Verification performed
- [ ] Alternative explanations examined empirically
- [ ] Critical data quality issues addressed

### Gate 4 — Publication Readiness Gate

- [ ] Claim Evidence consistency after results
- [ ] Major Referee issues addressed
- [ ] Figures and tables traceable
- [ ] References fully verified
- [x] Current limitations documented
- [ ] Conclusion supported by primary evidence
- [ ] Manuscript internally consistent

## Recent Changes

- ThemeをRQ-01/RQ-02へ具体化。
- literature map、gap、criteria、falsification planを作成。
- semantic feature scaffold、unit tests、initial reportを追加。

## Decision Log

| Decision ID | Date | Related RQ | Changed Item | Previous State | New State | Reason | Supporting Evidence | Impact | Human Approval |
|---|---|---|---|---|---|---|---|---|---|
| D-002 | 2026-09-16 | ALL | Research topic | Template | Semantic data model for IEQ prediction | User theme | user instruction | starts workflow | Not required |
| D-003 | 2026-09-16 | RQ-01 | Novelty framing | generic application | incremental value/generalization ablation | prior semantic IEQ work exists | L-CPW-01/02 | avoids overclaim | Not required |

## Next Actions

1. matched public dataset+semantic modelの取得可能性を確定する。
2. targetをdataに基づき固定する。
3. provenance/quality checks後、three-condition experimentを実行する。
4. edge ablation、alternative model、building bootstrapで検証する。
5. Referee再査読後にpaperを完成する。

## Final Report Delivery

- Execution mode: NON_STOP
- Final response format: INTEGRATED_RESEARCH_REPORT
- Report artifact: `results/reports/ieq_semantic_research_report.md`
- Report status: INITIAL_REPORT_COMPLETE / EMPIRICAL_RESULTS_BLOCKED_BY_DATA
