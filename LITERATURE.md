# LITERATURE

## Literature Review Status

- Overall status: INITIAL_REVIEW_COMPLETE; CLOSEST-WORK SEARCH CONTINUES
- Last search date: 2026-09-16
- Search scope: IEQ prediction、semantic web/ontology、Brick/BOP、portable analytics、cross-building generalization、comfort databases。
- Stop criteria: methodology designには十分。novelty確定には追加database searchが必要。

## Foundational Work

| ID | Source | Original Checked | Related RQ | Relevance | Evidence Label | Classification |
|---|---|---|---|---|---|---|
| L-001 | Brick Consortium, https://brickschema.org/ | YES | RQ-01, RQ-02 | entities/relationships/timeseries reference | DIRECT_EVIDENCE | READ |
| L-002 | Fierro et al., DOI:10.1145/3366375 | YES | RQ-02 | Brick-based portable analytics testbed | DIRECT_EVIDENCE | CRITICAL |
| L-003 | Földes et al., DOI:10.1016/j.buildenv.2018.06.022 | YES | RQ-01 | thermal-comfort research resource | DIRECT_EVIDENCE | READ |

## Closest Prior Work

| ID | Source | Original Checked | Same / Different RQ | Difference | Proposed Knowledge | Classification |
|---|---|---|---|---|---|---|
| L-CPW-01 | Donkers et al., DOI:10.1016/j.buildenv.2024.111319 | YES (record/abstract) | semantic integration and personal comfort | selection/contextを分離しbuilding-held-out generalizationとeffortをablation | incremental value and cost-benefit | CRITICAL |
| L-CPW-02 | Donkers et al., DOI:10.3390/buildings12101522 | YES (open article) | IEQ ontology design | ontology設計でなくgeneralization評価 | 有効/無効条件 | CRITICAL |
| L-CPW-03 | Tang et al., DOI:10.1016/j.enbuild.2022.111870 | YES (record/abstract) | cross-dataset IEQ satisfaction prediction | semantic modelなし | contextによるgeneralization改善 | DEEP_REVIEW |

## Recent Primary Studies

| ID | Source | Related RQ | Main Finding | Limitation | Evidence Label | Classification |
|---|---|---|---|---|---|---|
| L-004 | Tang et al. 2022, DOI:10.1016/j.enbuild.2022.111870 | RQ-01 | 別datasetでprediction error増加 | semantic contextなし | DIRECT_EVIDENCE | READ |
| L-005 | Occupant detection with IEQ sensors, DOI:10.1016/j.buildenv.2024.111319 | RQ-01 | room contextでgeneralizationが変化 | targetはoccupancy | DIRECT_EVIDENCE | READ |
| L-006 | Indoor humidity spatial prediction, DOI:10.1016/j.buildenv.2022.108964 | RQ-01 | spatial graphがunlabeled positionsに有効 | ontology効果と未分離 | DIRECT_EVIDENCE | READ |

## Systematic Reviews

| ID | Source | Scope | Useful Synthesis | Primary Sources to Follow |
|---|---|---|---|---|
| L-007 | Donkers et al. 2022, DOI:10.3390/buildings12101522 | IEQ semantic web | topology/static/dynamic integration | BOT、SOSA/SSN、Brick、BOP |

## Competing Methods

| Method | Strength | Weakness | Relevance |
|---|---|---|---|
| Flat tabular ML | simple, interpretable baseline | building-specific mapping | mandatory baseline |
| Spatial/temporal graph model | spatial dependency | topology/data quality dependence | semantic-context candidate |
| Semantic digital twin | heterogeneous integration | contribution ablation needed | closest approach |
| Transfer learning | limited target data | different mechanism | comparison/future extension |

## Negative Contradictory Evidence

| Source | Claim Challenged | Finding | Follow-up |
|---|---|---|---|
| Tang et al. 2022 | modelが別buildingへgeneralizeする | cross-dataset error増加 | building-held-out evaluation |
| Brick/BOP sources | semanticsがaccuracyを自動改善する | integration capabilityはaccuracy evidenceではない | controlled ablation |

## Known Limitations

- graph completeness/correctnessが低いとcontext featureが誤りを増やし得る。
- building type、climate、occupancy、calibrationがconditionと交絡し得る。
- comfort voteとphysical-variable predictionは別taskである。
- ontology construction costを除外すると実務価値を過大評価する。

## Relevant Standards

| Standard | Source | Relevance | Checked |
|---|---|---|---|
| ANSI/ASHRAE 55 | official licensed source required | thermal comfort evaluation | PENDING |
| ISO 7730 | official licensed source required | PMV/PPD | PENDING |
| W3C BOT | https://w3c-lbd-cg.github.io/bot/ | topology vocabulary | PENDING_DEEP_REVIEW |

## Cross-disciplinary References

| Field | Imported Concept | Contribution | Transfer Risk |
|---|---|---|---|
| Semantic Web/RDF | typed graph/query/validation | portable assembly | completeness != validity |
| Domain generalization | grouped hold-out | unseen-building claim | few buildings, wide uncertainty |
| Software portability | setup time/code change | RQ-02 | operator confounding |

## Research Gap Synthesis

Semantic models can integrate building/IEQ data and configure portable applications; semantic-digital-twin comfort studies already exist。したがってgapは「未利用」ではなく、graph-derived contextがautomated selectionを超えて予測に与える増分価値と、modeling effortを含むcost-benefitが未確定な点にある。

## Novelty Assessment

- Difference: flat、semantic-selection、semantic-contextの三条件ablation。
- Knowledge: prediction、portability、failure conditionを同時評価。
- `NOVELTY_INSUFFICIENT`: NOT_TRIGGERED_WITH_CURRENT_EVIDENCE。
- Risk: 同等比較の見落とし。publication claim前にcitation-chain/database searchが必要。

## Unresolved Literature Questions

- [ ] Donkers et al. 2024 full methods/resultsで同等ablationを確認。
- [ ] Brick/BOP/BOTの必要最小profileを決定。
- [ ] timeseriesとsemantic modelが同一IDで結合できるdatasetを確定。
- [ ] targetをCO₂、comfort vote、overall IEQ satisfactionからdataに基づき固定。

