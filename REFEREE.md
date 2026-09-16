# REFEREE

REFEREE_DECISION: MAJOR_REVISION_REQUIRED

## Topic Review

- Problem Definition: PASS
- Research Gap: PROVISIONAL_PASS
- RQ clarity: PASS
- Novelty: PROVISIONAL; full closest-work chain incomplete
- Scope: PASS after limiting primary outcome and three conditions
- Invalidity codes: `DATA_INSUFFICIENT` not yet triggered because acquisition alternatives remain; other codes not triggered。

## Scientific and Technical Review

- Claim–Evidence alignment: PASS (claims remain OPEN)
- Methodology validity: PROVISIONAL_PASS
- Data quality/provenance: NOT_READY
- Evaluation design: PASS_FOR_PROTOCOL
- Independent verification: PLANNED
- Alternative explanations: IDENTIFIED
- Falsification attempt: DESIGNED, NOT_RUN
- Reproducibility: SOFTWARE_SCAFFOLD_ONLY

## Publication Readiness Review

- Target journal fit: plausible, not selected
- Manuscript completeness: NOT_READY
- Contribution clarity: PROVISIONAL
- Limitations: documented
- Figures/tables/references: incomplete
- Expected concern: semantics may improve integration but not prediction; small number of buildings; ontology mapping cost; leakage through building identity。

## Critical Issues

| Issue ID | Related RQ / Claim | Issue | Why Critical | Required Revision | Status |
|---|---|---|---|---|---|
| RF-002 | CL-01, CL-02 | no empirical evidence | central claims cannot be evaluated | acquire matched multi-building data and run predefined evaluation | OPEN |

## Major Issues

| Issue ID | Related RQ / Claim | Issue | Required Revision | STATUS Task | Status |
|---|---|---|---|---|---|
| RF-001 | RQ-01 | target variable not fixed | fix after data feasibility | T-004 | OPEN |
| RF-003 | Novelty | equivalent ablation may exist | deep review and citation-chain search | TBD | OPEN |

## Minor Issues

| Issue ID | Issue | Suggested Revision | Status |
|---|---|---|---|
| RF-004 | toy graph predicates are generic, not Brick IRIs | replace with ontology profile in empirical implementation | OPEN |

## Falsification Attempts

| Attempt ID | Claim | Counterexample / Failure Mode | Test | Result | Impact |
|---|---|---|---|---|---|
| FA-01 | CL-01 | improvement is building-ID leakage | remove IDs, grouped split, permutation | NOT_RUN | critical |
| FA-02 | CL-01 | gain comes only from feature count | matched-dimensional baseline | NOT_RUN | major |
| FA-03 | CL-01 | wrong/incomplete graph worsens error | edge deletion/randomization | NOT_RUN | major |
| FA-04 | CL-02 | ontology modeling effort exceeds saved setup time | include end-to-end labor | NOT_RUN | critical |

## Alternative Explanations

| Claim / Result | Alternative Explanation | Discriminating Test | Status |
|---|---|---|---|
| future MAE gain | extra features rather than semantics | matched feature count/control | OPEN |
| future cross-building gain | similar climate/building type | leave-climate/type-out sensitivity | OPEN |
| future setup reduction | expert operator bias | counterbalanced operators | OPEN |

## Verification Concerns

- primary unit of generalization must be building, not row。
- semantic mapping must be frozen without test-label knowledge。
- missing graph relations must remain observable and enter error analysis。
- uncertainty must be computed across buildings, not only timestamps。

## Required Revisions

| Revision ID | Source Issue | Required Action | Owner / Role | Output | Status |
|---|---|---|---|---|---|
| REV-01 | RF-002 | acquire and validate dataset | Data Requirement | PROJECT/STATUS | BLOCKED |
| REV-02 | RF-002 | run ablation and falsification | Analysis/Verification | results | BLOCKED |
| REV-03 | RF-003 | deep closest-work review | Literature | LITERATURE.md | TODO |

## Resolved Issues

| Issue ID | Resolution | Evidence | Rechecked By Referee | Date |
|---|---|---|---|---|
| Initial overclaim | changed from generic semantic application to incremental-value ablation | PROJECT.md | YES | 2026-09-16 |

## Final Referee Decision

- Decision: MAJOR_REVISION_REQUIRED
- Rationale: protocol is testable and scoped, but central evidence is absent。
- Unresolved CRITICAL: 1
- Unresolved MAJOR: 2
- Gate 4 recommendation: NOT_READY

