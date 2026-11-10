# PROJECT

安定した研究設計の正本。日々の進捗、task、判断履歴は`STATUS.md`へ記録する。不明で根拠のない項目は`要検討`とする。

## Research Background

要検討

## Motivation

要検討

## Problem Definition

要検討

## Research Objective

要検討

## Research Questions

各RQは`literature/gaps.csv`でGap Challengerが`ACCEPTED / NARROWED`としたgapに基づく。Gap IDs列は`code/data/discovery.py audit`が検査する。

| RQ ID | Research Question | Gap IDs | Type | Status |
|---|---|---|---|---|
| RQ-01 | 要検討 | 要検討 | Primary | DRAFT |

## Initial Scope

- In scope: 要検討
- Out of scope: 要検討
- Constraints (time, people, compute, measurement, access): 要検討

## Systematic Evidence Review Scope

- Review ID: SR-001
- Review type: systematic review / systematic map / scoping review → 要検討
- Review question and RQ mapping: 要検討
- Framework: PCC / PICO / PICOC / SPIDER → 要検討
- Protocol artifact: `literature/protocol.json`
- Domain scope: building systems / indoor environment / building information / energy / topic-specific adjacent fields → 要検討
- Date range: 要検討
- Languages: 要検討
- Publication types: 要検討
- Planned databases and indexes: 要検討
- Topic-relevant seed-journal domains: 要検討
- Grey-literature and conference policy: 要検討
- Quality appraisal method by study design: 要検討
- Synthesis and gap taxonomy: 要検討
- Protocol lock status: DRAFT

### Protocol Amendments

| Amendment ID | Date | Previous | New | Reason | Impact | Re-screening Required | Approval |
|---|---|---|---|---|---|---|---|
| なし | - | - | - | - | - | - | - |

## Expected Contribution

開始時は未定でもよい。文献と問題定義で裏付けられるまで仮説として扱う。

- 要検討

## Research Resources

ユーザーの添付資料は`inputs/attachments.csv`に登録され、種類ごとに文献、data、本fileへ振り分けられる。添付由来の行はSourceに`USER_PROVIDED ATT-xxx`と書く。

| Category | Source | Purpose | Related RQ | Availability / Access Status |
|---|---|---|---|---|
| URLs | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| DOI / Literature | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| PDFs | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| Datasets | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| Repositories / Code | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| BIM / IFC / Drawings | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| Measurement / BMS / IoT Data | 要検討 | 要検討 | RQ-01 | UNKNOWN |
| Standards / Regulations | 要検討 | 要検討 | RQ-01 | UNKNOWN |

## Problem, Gap, and Novelty Assessment

- Closest Prior Work: 要検討（詳細は`LITERATURE.md`）
- Research Gap: 要検討
- Difference from Prior Work: 要検討
- Knowledge Created by the Difference: 要検討
- Scientific or Methodological Contribution: 要検討
- Assessment codes: `NONE / NOVELTY_INSUFFICIENT / DATA_INSUFFICIENT / NOT_VERIFIABLE / SCOPE_PROBLEM`
- Current assessment: 要検討

## RQ Mapping

### RQ-01

| Field | Value |
|---|---|
| RQ ID | RQ-01 |
| Research Question | 要検討 |
| Hypothesis | 要検討 |
| Motivation | 要検討 |
| Required Data | 要検討 |
| Available Data | 要検討 |
| Missing Data | 要検討 |
| Acquisition Method | 要検討 |
| Method | 要検討 |
| Evaluation Metric | 要検討 |
| Evaluation Criterion | 要検討 |
| Expected Evidence | 要検討 |
| Independent Verification | 要検討 |
| Expected Claim | 要検討 |
| Main Risk | 要検討 |

## Methodology Design

### Required Evidence

- RQ-01: 要検討

### Candidate Methods and Selection

| Method | Related RQ | Fit | Data Availability | Validity | Cost | Reproducibility | Interpretability | Scalability | Domain Suitability | Verification Feasibility | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 要検討 | RQ-01 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | PENDING |

### Evaluation and Verification Plan

| RQ | Metric | Criterion | Baseline / Reference | Expected Direction | Uncertainty / Error | Independent Verification Method |
|---|---|---|---|---|---|---|
| RQ-01 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 |

この表の確定値はGate 2の最後に`evidence/analysis_plan.json`へ転記してlockする。lock後の変更はplanのamendmentとして記録する。

## Data Inventory and Provenance

machine-readable正本は`data/manifest.json`。この表は要約として同じData IDで一致させる。取得は`code/data/acquire.py`、使用前検査は`code/data/quality.py`で行う。

| Data ID | Data Source | Owner | Acquisition Method | Device / System | Variable | Unit | Sampling Interval | Timestamp / Timezone | Coverage | Location | Equipment / Room Mapping | Calibration | Missing / Outliers | Preprocessing / Aggregation / Exclusion | Version | Access | Related RQ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DATA-01 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | 要検討 | UNKNOWN | RQ-01 |

### Data quality pre-use checklist

各項目は`code/data/quality.py profile`の結果（`results/data_quality/<DATA-ID>.json`）で確認する。train/test separationとleakageは`code/analysis/stats.py`のrolling-origin splitとtemporal leakage checkで確認する。

- [ ] Unit consistency
- [ ] Timestamp and timezone consistency
- [ ] Missing and duplicate records
- [ ] Sensor validity and calibration
- [ ] Spatial and equipment mapping
- [ ] Sampling interval and coverage
- [ ] Outlier handling
- [ ] Preprocessing traceability
- [ ] Train/test separation and data leakage

## Specialists

RQ、Method、Data、Evaluationに必要な場合だけ記入する。専用の常設fileは作らない。

| Role | Reason | Scope | Output Location | Status |
|---|---|---|---|---|
| 要検討 | 要検討 | 要検討 | PROJECT.md / STATUS.md / LITERATURE.md / REFEREE.md | NOT_ACTIVATED |

## Publication

- Candidate journal / venue: 要検討
- Target audience: 要検討
- Final journal selection: Human researcher
- Citation style: Numeric `[1]`, first-citation order
- Final report format: Render-verified PDF
- Delivery channel: Gmail connector
- Recipient source: Runtime configuration / explicit user instruction; do not commit address

## Report Design

- Report type: systematic review / evidence map / empirical study / method study / prototype validation / case study / negative or blocked report / mixed → 要検討
- Primary audience: 要検討
- Communication objective: 要検討
- Adaptive outline: 要検討
- Structure rationale: research type / evidence volume / result complexity / audience / venue → 要検討
- Expected emphasis: 要検討
- Sections intentionally merged, renamed, or omitted: 要検討
- Length constraint: NONE unless user or target venue specifies one
- Target venue formatting constraint: 要検討

## Database and External Access Plan

| Resource ID | Database / API / Connector | Purpose | Required for Central Claim | Access Status | Authentication / License Constraint | Alternative | Search / Retrieval Record |
|---|---|---|---|---|---|---|---|
| EXT-001 | ScienceDirect | Elsevier journal sweep and full-text verification | Topic dependent | USER_CONFIRMED_INSTITUTIONAL_ACCESS; VERIFY_AT_RUNTIME | Use authenticated browser session; never store credentials/cookies | DOI, institutional repository, author manuscript | `literature/search_log.csv` / STATUS.md |
| EXT-002 | Other bibliographic / domain databases | Cross-publisher discovery and citation coverage | Topic dependent | NOT_CHECKED | Subscription/API availability varies | OpenAlex, Crossref, publisher and repository search | `literature/search_log.csv` / STATUS.md |

## Security and Access

- Default access classification: `PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED` → 要検討
- Secret/data handling constraints: 要検討

