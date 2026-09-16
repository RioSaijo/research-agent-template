# PROJECT

## Research Background

Indoor Environmental Quality (IEQ)予測では、室温、相対湿度、CO₂、照度、騒音、在室、外気条件などの時系列を統合する必要がある。しかしBMS/IoTのpoint名、空間構成、設備との関係は建物ごとに異なるため、feature assemblyが個別実装になりやすく、別建物へのmodel移植時に性能と再利用性が低下する。

Brick、BOT、BOP等のbuilding semantic data modelは、sensor、room、zone、equipment、property、timeseries referenceの関係をmachine-readableに表現できる。既存研究はdata integration、portable analytics、personal comfort modelingの可能性を示しているが、semantic context自体がIEQ予測の建物間generalizationへ与える増分効果を、flat baselineとのcontrolled comparisonで評価する余地がある。

## Motivation

IEQ prediction pipelineを建物ごとのpoint-name mappingから切り離し、意味・空間・設備関係に基づいて自動構成できれば、再利用性が上がる可能性がある。一方、semantic modelの構築costに対して予測性能が改善しない可能性もあるため、accuracyだけでなくportabilityとengineering effortを同時に評価する。

## Problem Definition

Building semantic data modelを採用するだけでは予測性能向上は保証されない。必要なのは、同一のraw timeseriesと同一のlearning algorithmを使い、semantic graphから得たcontextual featuresと自動feature selectionの追加効果を、unseen building/zoneで比較することである。

## Research Objective

Building semantic data modelから自動抽出した空間・設備・sensor contextが、IEQ予測の建物間generalization、feature assembly再利用性、保守性へ与える効果と限界を定量評価する。

## Research Questions

| RQ ID | Research Question | Type | Status |
|---|---|---|---|
| RQ-01 | Semantic graphから抽出したspace/equipment/sensor contextは、flat timeseries baselineよりunseen building/zoneでのIEQ予測誤差を低減するか | Primary | READY_FOR_DATA |
| RQ-02 | Semantic queryによるfeature assemblyは、手作業mappingに比べて新規buildingへの適用作業を削減し、必要pointのcoverageを維持できるか | Secondary | READY_FOR_DATA |

## Initial Scope

- In scope: room/zone-levelのCO₂またはthermal-comfort proxyの短期予測、Brick互換RDF graph、space/equipment/sensor relation、建物単位hold-out評価。
- Out of scope: clinical health outcome、fully autonomous HVAC control、ontology自体の新規標準化、causal effectの断定、単一building random splitだけによる一般化主張。
- Constraints: 実測datasetと対応semantic modelは未提供。現在の成果はliterature-backed protocolとtested software scaffoldまで。

## Expected Contribution

- `[PRELIMINARY]` semantic contextの予測性能への寄与と、data integration/portabilityへの寄与を分離して評価するprotocol。
- `[PRELIMINARY]` flat、semantic-selection、semantic-contextの三条件によるablation design。
- `[PRELIMINARY]` RQ–Data–Method–Evidence–Claimを追跡できる最小実装。

## Research Resources

| Category | Source | Purpose | Related RQ | Availability / Access Status |
|---|---|---|---|---|
| URLs | https://brickschema.org/ | Brick schema/documentation | RQ-01, RQ-02 | PUBLIC |
| DOI / Literature | 10.3390/buildings12101522 | IEQ semantic web review and BOP | RQ-01, RQ-02 | PUBLIC |
| DOI / Literature | 10.1145/3366375 | Mortar portable analytics | RQ-02 | PUBLIC |
| DOI / Literature | 10.1016/j.buildenv.2024.111319 | Cross-domain semantic digital twin comfort model | RQ-01 | PUBLIC/OPEN ACCESS |
| DOI / Literature | 10.1016/j.buildenv.2018.06.022 | ASHRAE Global Thermal Comfort Database II | RQ-01 | PUBLICATION; DATA ACCESS TO VERIFY |
| Datasets | Project-specific building data | Final empirical evaluation | RQ-01, RQ-02 | NOT_PROVIDED |

## Problem, Gap, and Novelty Assessment

- Closest Prior Work: Donkers et al. (2024), personal indoor comfort models through cross-domain semantic digital twins。
- Research Gap: semantic integrationを用いたcomfort modelingは既知だが、semantic contextのincremental predictive valueとfeature-assembly portabilityを同じexperimentで分離評価する設計は、確認済み文献だけでは確立していない。
- Difference from Prior Work: ontology/framework提案ではなく、semantic利用のどの部分がaccuracy/generalization/engineering effortへ効くかをablationする。
- Knowledge Created by Difference: semantic enrichmentが有効な条件、無効な条件、cost-benefit境界。
- Current assessment: `NONE`（同等ablation研究が見つかれば`NOVELTY_INSUFFICIENT`を再評価）

## RQ Mapping

### RQ-01

| Field | Value |
|---|---|
| RQ ID | RQ-01 |
| Research Question | Semantic contextはunseen building/zoneでIEQ predictionを改善するか |
| Hypothesis | Semantic-context modelはflat baselineよりbuilding-held-out MAEを10%以上低減する |
| Motivation | 建物固有mappingとcontext欠落によるgeneralization低下を検証する |
| Required Data | 複数building/zoneのIEQ timeseries、weather、occupancy、semantic graph、target ground truth |
| Available Data | 文献とreference semantic models。対応済み実測datasetは未確保 |
| Missing Data | 同一entity IDで結合できるtimeseries、graph、target |
| Acquisition Method | 公開dataset+semantic mapping、またはproject BMS/IoT dataをBrickへmapping |
| Method | flat/semantic-selection/semantic-context ablation |
| Evaluation Metric | MAE(primary), RMSE, R²; classification時はmacro-F1/AUROC |
| Evaluation Criterion | building-held-out MAE 10%以上改善かつ95% bootstrap CIが0を跨がない |
| Expected Evidence | building-wise prediction table、paired error distribution、ablation、coverage/error analysis |
| Independent Verification | alternative model family、permutation test、semantic-edge ablation |
| Expected Claim | semantic contextがどの条件でgeneralizationを改善/改善しないか |
| Main Risk | dataset/graph alignment不足、building confounding、semantic feature leakage |

### RQ-02

| Field | Value |
|---|---|
| RQ ID | RQ-02 |
| Research Question | Semantic queryはfeature assembly作業を削減しcoverageを維持するか |
| Hypothesis | 新規building setup timeを30%以上削減し、required-point recall 0.95以上を達成する |
| Motivation | accuracy以外のportable analytics価値を測る |
| Required Data | building models、required point list、manual/semantic setup logs、mapping ground truth |
| Available Data | Brick reference modelsは候補。task logsは未取得 |
| Missing Data | independent annotatorによるmapping ground truthと作業時間 |
| Acquisition Method | 複数buildingでcounterbalanced mapping study |
| Method | graph traversal/SPARQLとmanual baseline比較 |
| Evaluation Metric | setup time、required-point precision/recall、unresolved mappings、code changes |
| Evaluation Criterion | median setup time 30%以上削減、recall ≥0.95、重大な誤mappingなし |
| Expected Evidence | task log、mapping confusion table、repository diff |
| Independent Verification | 第二annotator、SHACL validation、sample manual audit |
| Expected Claim | semantic modelのintegration portabilityへの効果 |
| Main Risk | manual baseline skill差、ontology qualityへの依存 |

## Methodology Design

### Experimental conditions

1. Flat baseline: manually selected raw sensor/weather/time features。
2. Semantic-selection: graph queryで同等featureを自動選択するがgraph-derived contextは入力しない。
3. Semantic-context: selectionに加え、room type、adjacency、served-by equipment、sensor role、zone aggregation等を入力する。

建物単位でtrain/validation/testを分離する。random row splitは主要評価に使わない。各conditionで同一model familyと同一hyperparameter budgetを用いる。

### Evaluation and Verification Plan

| RQ | Metric | Criterion | Baseline / Reference | Expected Direction | Uncertainty / Error | Independent Verification Method |
|---|---|---|---|---|---|---|
| RQ-01 | building-held-out MAE | ≥10% reduction; bootstrap 95% CI excludes 0 | Flat baseline | Lower | building bootstrap | model-family replication、edge ablation、permutation test |
| RQ-02 | setup time; mapping recall | ≥30% time reduction; recall ≥0.95 | Manual mapping | Lower time, high recall | operator effect | second annotator、SHACL、manual audit |

## Data Inventory and Provenance

| Data ID | Data Source | Owner | Acquisition Method | Variable | Unit | Sampling Interval | Timestamp / Timezone | Coverage | Mapping | Calibration | Missing / Outliers | Preprocessing | Version | Access | Related RQ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DATA-01 | Project BMS/IoT or matched public dataset | TBD | API/export | CO₂, temperature, RH, occupancy, weather | ppm/°C/%/count | 5–15 min target | required | ≥1 season preferred | Brick graph required | required | documented | train-only fit | TBD | NOT_ACQUIRED | RQ-01 |
| DATA-02 | Brick/BOP model | Building owner/repository | RDF export/mapping | classes/relations/units/references | RDF | static | n/a | all buildings | mapping source | SHACL | missing edges logged | no label-derived edits | fixed | FEASIBILITY_REVIEW | RQ-01, RQ-02 |

## Specialists

| Role | Reason | Scope | Output Location | Status |
|---|---|---|---|---|
| Semantic Web / Ontology | graph modeling and validation | feature assembly | code/integration, PROJECT.md | ACTIVATED |
| Building/IEQ | target and sensor validity | RQ/evaluation review | PROJECT.md, REFEREE.md | REQUIRED_FOR_EMPIRICAL_PHASE |
| Statistics/ML | grouped validation and uncertainty | evaluation | code/analysis, results | REQUIRED_FOR_EMPIRICAL_PHASE |

## Publication

- Candidate venues: Building and Environment; Journal of Building Engineering; Automation in Construction; BuildSys。
- Target audience: building performance、smart buildings、semantic interoperability、data-driven IEQ。
- Final journal selection: Human researcher。

## Security and Access

- Default classification: `INTERNAL` until dataset terms are reviewed。
- occupant feedback/occupancy dataはpersonal informationとしてde-identification、access control、purpose limitationを確認する。

