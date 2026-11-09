# STATUS

現在の研究状態と運用管理の正本。Research Managerが更新する。

## PROJECT_STATUS

`TRIAGE`

Allowed: `TRIAGE / ACTIVE / REFRAMING / VALIDATION / WRITING / COMPLETE / PARKED`

## CURRENT_PHASE

`Intake`

## Research Maturity

- Stage: TO_DEFINE（S0 関心領域 / S1 問題意識 / S2 RQ案 / S3 設計済み / S4 継続・改訂）
- Route: TO_DEFINE（EXPLORATION / SYSTEMATIC_REVIEW / METHODOLOGY / REVISION）
- Record: `inputs/intake.json`
- Attachments: `inputs/attachments.csv`（0件）
- Pending human decision: なし

## CURRENT_GATE

`Gate 1 — Research Definition Gate`

## Current Research Questions

| RQ ID | Summary | Status | Critical Issue |
|---|---|---|---|
| RQ-01 | 要検討 | DRAFT | Problem Definition and literature evidence incomplete |

## Current Findings

- なし

## Claim Evidence Table

Data Originは`OBSERVED / GENERATED / MIXED`。GENERATEDまたはMIXEDのclaimは、生成dataに基づくことを本文でも明示する。

| Claim ID | RQ | Claim | Evidence Type | Data Origin | Primary Evidence | Independent Check | Verification | Claim Status | Referee |
|---|---|---|---|---|---|---|---|---|---|
| CL-01 | RQ-01 | 要検討 | LITERATURE | 要検討 | なし | 要検討 | NOT_VERIFIED | OPEN | NOT_REVIEWED |

## Current Tasks

| Task ID | Related RQ | Task | Purpose | Owner / Role | Dependency | Required Resource | Output | Status | Priority | Blocking Issue | Related Quality Gate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T-000 | ALL | briefと添付を登録し成熟度を判定する | 開始点と人間の判断点を決める | Intake Coordinator | None | User message / attachments | inputs/intake.json / inputs/attachments.csv | TODO | P0 | None | Gate 1 |
| T-001 | RQ-01 | Required inputを確認する | 研究入力を確定する | Research Manager | T-000 | inputs/intake.json | PROJECT.md | TODO | P0 | None | Gate 1 |
| T-027 | RQ-01 | 予備調査で問題・RQの選択肢を示す（S0/S1のみ） | 人間が研究の方向を選べるようにする | Exploration Analyst | T-000 | Brief / attachments / light search | inputs/intake.json / results/exploration/ | BLOCKED | P0 | Stage not judged | Gate 1 |
| T-002 | RQ-01 | closest prior workとgapを調べる | noveltyと問題定義を評価する | Literature Role | T-001 | Web / literature | LITERATURE.md | TODO | P0 | Input incomplete | Gate 1 |
| T-003 | RQ-01 | data requirementと取得経路を設計する | feasibilityを評価する | Data Requirement Role | T-001 | Resource inventory | PROJECT.md | TODO | P1 | Input incomplete | Gate 2 |
| T-004 | RQ-01 | method/evaluation/verificationを設計する | analysis前提を整える | Methodology Role | T-002, T-003 | Literature / data status | PROJECT.md | BLOCKED | P1 | Dependencies incomplete | Gate 2 |
| T-005 | RQ-01 | journal掲載論文を検索・選定する | closest workと方法根拠を査読文献で確認する | Literature Role | T-001 | Publisher / DOI / scholarly index | LITERATURE.md | TODO | P0 | Input incomplete | Gate 1 |
| T-006 | ALL | 引用番号付きPDFを生成・render検証する | 読める最終artifactを作る | Writer / Verification | Gate 4 | Manuscript / report source | results/reports/*.pdf | BLOCKED | P1 | Gate 4 incomplete | Gate 5 |
| T-007 | ALL | PDFをGmail送信しdeliveryを記録する | workflowを完了する | Research Manager | T-006 | Gmail connection / runtime recipient | STATUS.md delivery record | BLOCKED | P1 | PDF not verified | Gate 5 |
| T-008 | RQ-01 | systematic review protocolをlockする | review scopeとeligibilityを事前固定する | Review Protocol Lead | T-001 | Research theme | literature/protocol.json | TODO | P0 | Input incomplete | Gate 1 |
| T-009 | RQ-01 | database別queryを設計・査読する | recallと再現性を確保する | Search Strategist / Search Peer Reviewer | T-008 | Vocabulary / sentinel papers | literature/search_log.csv | BLOCKED | P0 | Protocol not locked | Gate 1 |
| T-010 | RQ-01 | databaseとseed journalを収集する | high-coverage corpusを構築する | Database / Journal Harvester | T-009 | Database / web access | literature/records.csv | BLOCKED | P0 | Query not approved | Gate 1 |
| T-011 | RQ-01 | metadata統合と重複除去を行う | retrieval provenanceを保った一意corpusを作る | Metadata Curator | T-010 | Retrieved records | literature/records.csv | BLOCKED | P0 | No records | Gate 1 |
| T-012 | RQ-01 | title/abstractとfull textを二重screeningする | 恣意的選定を抑える | Screener A / B / Adjudicator | T-011 | Eligibility criteria / full text | literature/screening_decisions.csv | BLOCKED | P0 | Dedup incomplete | Gate 1 |
| T-013 | RQ-01 | quality appraisalとevidence extractionを行う | gap synthesisの証拠を構造化する | Quality Appraiser / Evidence Extractor | T-012 | Included studies | literature/extraction.csv | BLOCKED | P0 | Screening incomplete | Gate 1 |
| T-014 | RQ-01 | citation chasingとgap challengeを完了する | 検索漏れと偽gapを反証する | Citation Chaser / Gap Analyst / Gap Challenger | T-013 | Included studies / citation graph | LITERATURE.md | BLOCKED | P0 | Extraction incomplete | Gate 1 |
| T-015 | RQ-01 | systematic reviewを独立監査する | PRISMA、coverage、判定、gap traceabilityを確認する | Review Auditor | T-014 | Review artifacts | LITERATURE.md / results/literature/prisma_flow.json | BLOCKED | P0 | Gap challenge incomplete | Gate 1 |
| T-022 | RQ-01 | gapを`literature/gaps.csv`へ記録し独立にchallengeする | RQの根拠となるgapを反証可能にする | Gap Analyst / Gap Challenger | T-013 | Extraction / search log | literature/gaps.csv | BLOCKED | P0 | Extraction incomplete | Gate 1 |
| T-023 | RQ-01 | data requirementを逆算する | RQに必要なdataだけを定義する | Data Requirement Role | T-022, T-016 | Gaps / analysis plan | data/requirements.csv | BLOCKED | P1 | Gap not accepted | Gate 2 |
| T-024 | RQ-01 | pathway別にdata sourceを探索する | public/literature/API/measurement/simulation/proxyを網羅する | Data Source Scout | T-023 | Repositories / connectors / web | data/source_search_log.csv / data/candidates.csv | BLOCKED | P1 | No requirements | Gate 2 |
| T-025 | RQ-01 | candidate datasetを採点・選定する | fit、coverage、quality、access、reproducibilityで選ぶ | Data Screener | T-024 | Candidates | data/candidates.csv / data/manifest.json | BLOCKED | P1 | No candidates | Gate 2 |
| T-026 | RQ-01 | 収集不能なdataを生成・検証する（必要時のみ） | 全collection pathway失敗後にラベル付き生成dataで研究を継続する | Data Generator / Generated Data Validator | T-024 | Observed reference data / generator | data/generated/ / results/data_validation/ / evidence/checks.csv | BLOCKED | P2 | Collection pathways not exhausted | Gate 2 |
| T-020 | RQ-01 | data manifestを作成しraw dataを取得・登録する | provenanceとhash付きでdataを確保する | Data Requirement Role | T-003 | Data source / access | data/manifest.json / data/raw/ | BLOCKED | P1 | Data requirement incomplete | Gate 2 |
| T-021 | RQ-01 | pre-use data quality profileを実行する | unit、時刻、欠損、range、sensor異常を分析前に検出する | Data Requirement Role | T-020 | Raw data | results/data_quality/ / evidence/checks.csv | BLOCKED | P1 | No data | Gate 2 |
| T-016 | RQ-01 | analysis planをlockする | 結果を見る前にcriterion、claim type、required check、independence levelを固定する | Methodology Role | T-004 | PROJECT.md evaluation plan | evidence/analysis_plan.json | BLOCKED | P1 | Methodology incomplete | Gate 2 |
| T-017 | RQ-01 | primary analysisを実行しrunを記録する | provenanceとhash付きprimary evidenceを作る | Analysis Role | T-016 | Data / code | evidence/runs.csv / results/ | BLOCKED | P1 | Plan not locked | Gate 3 |
| T-018 | RQ-01 | challenge checkを実施する | 代替説明、sensitivity、falsification、leakageを分析者以外が検査する | Methods Challenger | T-017 | Primary run | evidence/checks.csv | BLOCKED | P1 | No primary run | Gate 3 |
| T-019 | RQ-01 | 独立検証とGate 3 auditを行う | plan指定のindependence levelでclaimを検証し、strict auditを通す | Verification / Evidence Auditor | T-018 | Checks / runs | evidence/claims.csv / results/evidence/gate3_report.json | BLOCKED | P1 | Checks incomplete | Gate 3 |

## Blocked Tasks

| Task ID | Blocker | Resolution Path | Human Required |
|---|---|---|---|
| T-004 | T-002 and T-003 incomplete | Complete prerequisites | NO |

## Required Human Input

| Input ID | Reason | Decision Needed | Effect if Deferred | Status |
|---|---|---|---|---|
| H-001 | RQや主要scopeを変更する場合のみ使用 | 要検討 | Current approved direction remains unchanged | NOT_REQUIRED |

## Data Status

- Required data: 要検討
- Available data: 要検討
- Missing data: 要検討
- Acquisition feasibility: 要検討
- Provenance status: NOT_REVIEWED
- Data quality status: NOT_REVIEWED

## Implementation Status

- Full implementation readiness: NOT_READY
- Repository/code state: TEMPLATE_ONLY
- Reproducibility checks: NOT_RUN

## Verification Status

- Evaluation Criterion defined: NO
- Primary Evidence exists: NO
- Criterion applied: NO
- Alternative explanations examined: NO
- Independent verification required/plan: 要検討
- Verification state: NOT_VERIFIED

## Referee Issues

| Issue ID | Stage | Severity | Related RQ / Claim | Issue | Required Revision | Status | Task ID |
|---|---|---|---|---|---|---|---|
| RF-001 | Topic Review | NOTE | RQ-01 | Initial review pending | Complete Gate 1 inputs | OPEN | T-001 |

## Quality Gates

### Gate 1 — Research Definition Gate

- [ ] Intake recorded: stage, rationale, route, brief (`code/intake/intake.py audit`)
- [ ] Every attachment registered with hash, stored under `inputs/raw/`, and routed or rejected with a reason
- [ ] S0/S1 only: options presented and one selected by a human (Decision Log ID recorded)
- [ ] Systematic review protocol locked before screening
- [ ] Eligibility, date, language, publication type, sources, and synthesis plan defined
- [ ] Database-specific queries independently peer reviewed
- [ ] Planned databases and topic-relevant seed journals searched
- [ ] Search date, full query, filters, hits, and exports recorded
- [ ] No arbitrary maximum-reference cap applied
- [ ] Database/API result limits exhausted by pagination/query splitting or disclosed
- [ ] LOW_VOLUME_REVIEW trigger cleared by search expansion or justified niche scope
- [ ] Deduplication and related-report handling completed
- [ ] Independent dual title/abstract and full-text screening completed
- [ ] All conflicts resolved and exclusions have controlled reasons
- [ ] Included studies quality-appraised and evidence-extracted
- [ ] Backward/forward citation chasing and update search completed
- [ ] PRISMA counts agree with machine-readable records
- [ ] Gap candidates passed independent Gap Challenger review
- [ ] `literature/gaps.csv` records supporting/contradicting appraised studies, search IDs, and minimum closing design
- [ ] Every RQ references an ACCEPTED / NARROWED gap in PROJECT.md
- [ ] Background defined
- [ ] Motivation defined
- [ ] Problem Definition supported by literature
- [ ] Journal search log completed
- [ ] Closest primary journal articles checked at original source
- [ ] RQ defined
- [ ] Closest Prior Work identified
- [ ] Research Gap defined
- [ ] Scope reasonable

Failure state: `TRIAGE / REFRAMING`

### Gate 2 — Methodology Readiness Gate

- [ ] RQ Data Method mapping complete
- [ ] Required Data identified
- [ ] Reasonable acquisition path exists
- [ ] Every RQ has MUST data requirements derived from gap, metric, criterion, and baseline (`data/requirements.csv`)
- [ ] Each MUST requirement searched in data repositories and in data used by included studies; other pathways logged
- [ ] Candidate datasets scored against `data/screening_rubric.json` with cited anchors; MUST selections re-scored by a second role
- [ ] Candidate datasets screened and scored; selections have license, access, and manifest entry
- [ ] `DATA_INSUFFICIENT` declared only after every pathway was assessed
- [ ] Generated data used only for requirements whose collection pathways (public data, API, measurement, external provider) were all attempted; requirement status is GENERATED, never SATISFIED
- [ ] Generated datasets carry provenance_class, the fixed label, a data_origin column on every row, and a provenance sidecar under `data/generated/`
- [ ] Fidelity criteria fixed before generation; validation PASS recorded by a role other than the generator
- [ ] Strict `code/data/discovery.py audit` passes; `results/traceability/chain.json` generated
- [ ] Every dataset has a `data/manifest.json` entry (source, access, license, units, valid ranges, timezone, interval)
- [ ] Raw files acquired/registered with SHA-256 via `code/data/acquire.py`
- [ ] Pre-use quality profile run for every dataset; WARN/FAIL dispositions recorded
- [ ] Time-ordered split, multiplicity correction, and uncertainty method specified in the analysis plan
- [ ] Evaluation Metric defined
- [ ] Evaluation Criterion defined
- [ ] Baseline / Reference defined when required
- [ ] Verification Plan defined
- [ ] `evidence/analysis_plan.json` LOCKED (claim type, criterion, required checks, independence level) before any confirmatory run

### Gate 3 — Evidence and Verification Gate

Per-claim gate. Machine-readable source: `evidence/`. Judge with
`python code/evidence/evidence_audit.py report --status STATUS.md --verify-files`
(no `--allow-incomplete`); output `results/evidence/gate3_report.json`.

- [ ] Analysis plan locked before every confirmatory run; amendments recorded with re-analysis impact
- [ ] Every planned analysis has a PRIMARY run; every pre-registered claim reported, including negative results
- [ ] Every run records git commit, command, environment, seed, and input/output SHA-256 (via `code/analysis/record_run.py`)
- [ ] `code/data/acquire.py verify` passes: raw data unchanged since registration
- [ ] Recorded inputs/outputs exist and hashes match (no stale results)
- [ ] Criterion applied exactly as pre-registered; numeric criteria auto-evaluated without contradiction
- [ ] Uncertainty reported for every SUPPORTED / PARTIALLY_SUPPORTED claim
- [ ] Claim-type minimum checks passed (DATA_QUALITY; central: ALTERNATIVE_EXPLANATION, SENSITIVITY; CAUSAL: FALSIFICATION; PREDICTIVE: LEAKAGE, BASELINE; COMPARATIVE: BASELINE; GENERALIZATION: TRANSFER)
- [ ] Challenge and independent verification performed by roles other than the primary analyst
- [ ] Verification level matches the plan (RERUN is reproduction, not independent verification)
- [ ] Post-hoc claims kept at PRELIMINARY or lower
- [ ] FAIL / INCONCLUSIVE checks record their impact on the claim
- [ ] STATUS.md Claim Evidence Table matches `evidence/claims.csv`
- [ ] Claims using generated data carry `generated_data_disclosure` and Data Origin GENERATED / MIXED; claims on generated data alone are limited to statements about the model (no SUPPORTED causal or generalization claims)
- [ ] Strict evidence audit returns no issues

Failure state: `ACTIVE` (return to analysis/verification) / `REFRAMING` when criterion or claim type must change

### Gate 4 — Publication Readiness Gate

- [ ] Report type, audience, adaptive outline, and structure rationale recorded
- [ ] Report length and section depth follow evidence/result complexity rather than a fixed template
- [ ] Inapplicable sections omitted or merged without losing traceability
- [ ] Claim Evidence consistency
- [ ] Major Referee issues addressed
- [ ] Every CRITICAL / MAJOR issue has a Response to Referee
- [ ] Solution alternatives and selected rationale documented
- [ ] Revised artifacts and manuscript locations linked to each response
- [ ] Independent Referee re-review completed
- [ ] No CRITICAL / MAJOR issue has REJECTED or unresolved disposition
- [ ] Figures and tables traceable
- [ ] References verified (`code/literature/verify_refs.py bib`: every entry METADATA_VERIFIED, or ORIGINAL_CHECKED with location)
- [ ] Numeric in-text citations correspond to reference list
- [ ] Limitations documented
- [ ] Conclusion supported
- [ ] Manuscript internally consistent
- [ ] Database/API access limitations and their coverage impact disclosed
- [ ] Every generated dataset used by a claim is labeled with `\GeneratedData{ID}` in text, figures, and tables (`code/data/generate.py check-disclosure`)

### Gate 5 — Report Delivery Gate

- [ ] Final PDF generated under `results/reports/`
- [ ] Every page render-checked
- [ ] No clipping, overlap, missing glyph, or broken table/figure
- [ ] Numeric citations and references verified in the PDF
- [ ] Generated-data labels visible in the rendered PDF wherever generated data or derived results appear
- [ ] Gmail authenticated account confirmed
- [ ] Runtime recipient confirmed without committing personal information
- [ ] PDF sent as attachment
- [ ] Send response confirmed successful
- [ ] Delivery record completed below

## Recent Changes

- Repository initialized from specification.
- Mandatory end-to-end flow added: journal search, numeric citations, PDF render QA, Gmail delivery, and delivery recording.
- Gate 3 strengthened: locked analysis plan, machine-readable evidence registries, and strict evidence audit.
- Data and analysis toolkit added: data manifest, acquisition, quality profiling, statistics, and run recording.
- Research intake added: maturity stages S0-S4, exploration options, attachment register and routing.
- Generated data policy added: last-resort generation with mandatory labeling and separate-role fidelity validation.
- Expert agent roles single-sourced in `agents/roles.json` and generated for Claude Code and portable (ChatGPT / Codex) use.
- Problem-to-data chain added: machine-readable gaps, data requirements, data source search, candidate screening, and chain audit.

## Decision Log

| Decision ID | Date | Related RQ | Changed Item | Previous State | New State | Reason | Supporting Evidence | Impact | Human Approval |
|---|---|---|---|---|---|---|---|---|---|
| D-001 | YYYY-MM-DD | ALL | Repository initialization | None | Template v1.0.0 | Create reusable environment | JSON specification | Establishes workflow | Not required |
| D-010 | 2026-11-09 | ALL | Reference verification | Source checks done by hand; exploration could present unverified sources | verify_refs.py checks DOIs and bibliographic data against Crossref/OpenAlex; options need two verified sources; Gate 4 bib check | Exploration trial could not verify sources and correctly withheld options | Agent trial | Sources are verified mechanically before options or manuscripts use them | Template change |
| D-009 | 2026-11-09 | ALL | Research intake | Start required full background, problem, objective, and RQ; attachments unspecified | Intake stage S0-S4 with routes, exploration options for human selection, attachment register and routing | User asked prompts to cover varying idea maturity and to define attachment handling | Explicit user instruction | Requests at any maturity can start; attachments are traceable data, never instructions | Approved |
| D-008 | 2026-11-09 | ALL | Generated data policy | Uncollectable data led only to PROXY or DATA_INSUFFICIENT | Simulated / synthetic / augmented data allowed after all collection pathways fail, with mandatory labels in manifest, file rows, sidecar, runs, claims, STATUS.md, manuscript, and PDF, and separate-role fidelity validation | User asked to generate, validate, and use data when collection fails, always marked as generated | Explicit user instruction | Research can proceed without observed data while generated data stays distinguishable and claim strength is limited | Approved |
| D-007 | 2026-11-08 | ALL | Agent platform policy | ChatGPT-first, Codex-on-demand; roles only in prose | Platform-neutral roles single-sourced in agents/roles.json, generated for Claude Code and portable use, CI sync check | User required agents usable across platforms | Explicit user instruction | Any platform can run any role with identical rules and audits | Approved |
| D-006 | 2026-11-08 | ALL | Dataset screening rubric | Unanchored 0-3 scores | Anchored rubric DSR-1.0, rationale, second-role verification, SATISFIED minimum scores, cross-source DOI dedupe | Scores varied by screener and could not be audited | Live DataCite/Zenodo test and rubric review | Data selection becomes reproducible across screeners | Template change |
| D-005 | 2026-11-08 | ALL | Problem-to-data chain | Gap, RQ, and data needs linked only by prose | gaps.csv, requirements.csv, source search log, candidate screening, chain audit and matrix | Gap identification and data judgement, search, and selection were not traceable | Template review | Gate 1/2 gap and data decisions become auditable | Template change |
| D-004 | 2026-11-08 | ALL | Data and analysis toolkit | Manual data inventory and ad hoc analysis | Data manifest, acquisition with hashes, automated quality profile, shared statistics, recorded runs | Data collection and quantitative analysis lacked reproducible tooling | Template review | Gate 2/3 data and analysis items become machine-checkable | Template change |
| D-003 | 2026-11-08 | ALL | Gate 3 evidence control | Self-declared 7-item checklist | Locked analysis plan, run/check/claim registries, strict machine audit | Gate 3 lacked pre-registration, provenance hashes, check coverage, role separation, and independence levels | Template review | Gate 3 becomes per-claim and machine-verifiable | Template change |
| D-002 | 2026-09-16 | ALL | Completion workflow | Gate 4 ended at manuscript readiness | Gate 5 requires verified PDF and Gmail delivery | User required theme-to-email execution, journal search, and numeric citations | Explicit user instruction | Adds mandatory search, citation, rendering, and delivery controls | Approved |

## Next Actions

1. `PROJECT.md`のrequired inputを確認する。
2. 文献調査でclosest prior work、gap、noveltyを評価する。
3. journal検索source、query、検索日、採否、DOIを記録する。
4. data requirement、取得経路、quality/provenanceを設計する。
5. method、metric、criterion、baseline、verification planを設計する。
6. Gate 1からGate 5まで判定し、PDF送信記録を完了する。

## Final Report Delivery

- Execution mode: NON_STOP
- Final response format: INTEGRATED_RESEARCH_REPORT
- Routine phase approval: NOT_REQUIRED
- Human pause conditions: RQ change / major scope change / human-only resource / critical direction decision / PARK
- Report status: NOT_STARTED
- Citation format: NUMERIC_IN_TEXT
- Journal search status: NOT_STARTED
- PDF path: NOT_CREATED
- PDF render QA: NOT_RUN
- Recipient source: NOT_CONFIGURED
- Gmail account status: NOT_CHECKED
- Sent timestamp: NOT_SENT
- Gmail message ID: NOT_SENT
- Delivery status: NOT_SENT
