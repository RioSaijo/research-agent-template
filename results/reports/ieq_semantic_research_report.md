# Building Semantic Data Modelを活用したIEQ予測：初期研究報告書

## Executive Summary

本研究は、building semantic data modelを使うこと自体ではなく、semantic graphから得た空間・設備・sensor contextが、IEQ予測の建物間generalizationとfeature assemblyの再利用性を改善するかを検証対象とする。

初期文献調査では、IEQ向けontology、Brickを用いたportable analytics、semantic digital twinを用いたpersonal comfort modelは既に存在する。このため「semantic modelをIEQ予測に初めて使う」という新規性は成立しない。提案する新規性は、(1) flat baseline、(2) semantic-selection、(3) semantic-contextを分け、accuracyとengineering effortの両方を評価するcontrolled ablationにある。

現時点では対応する実測timeseriesとsemantic graphが未取得であり、予測性能に関するscientific claimは`OPEN`である。一方、RQ、評価基準、data requirement、反証条件、software scaffoldは作成した。

## Research Questions

- RQ-01: semantic contextはflat baselineよりunseen building/zoneでのIEQ prediction errorを低減するか。
- RQ-02: semantic queryによるfeature assemblyはmanual mappingよりsetup effortを削減し、required-point coverageを維持するか。

## Literature Positioning

- Brickはbuilding entityとrelationshipをRDFで記述し、timeseriesへのreferenceを持てる。
- BOP研究はIEQのtopology、static/dynamic property統合を目的にontologyを設計している。
- MortarはBrickを使ったportable building analyticsのtestbedを示す。
- cross-domain semantic digital twinからpersonal comfort modelを作る研究が既にある。
- IEQ predictionは別building/populationへの適用でerrorが増える場合があり、building-held-out evaluationが必要である。

## Proposed Method

同一のraw dataとmodel familyで三条件を比較する。

1. Flat baseline: manual feature mapping。
2. Semantic-selection: graph queryでfeatureを選ぶがcontextはmodelへ入れない。
3. Semantic-context: room type、adjacency、served-by equipment、sensor role等を入力する。

建物単位hold-outを主要評価とし、primary metricをMAEとする。RQ-01の事前criterionはMAE 10%以上低減かつbuilding bootstrap 95% CIが0を跨がないこと。RQ-02はsetup time 30%以上削減、required-point recall 0.95以上、重大な誤mappingなしとする。

## Falsification Plan

- semantic edgeをrandomize/removeして性能差が消えるか。
- semantic conditionだけにtest-building固有情報が入っていないか。
- model familyを変えて方向が再現するか。
- improvementが特定building、season、sensor completenessだけで決まっていないか。
- ontology mapping costを含めるとmanual baselineより不利にならないか。

## Current Evidence and Results

- Literature evidence: semantic integrationとportable analyticsのfeasibilityは支持される。
- Software evidence: explicit sensor→room→zone relationからcontextを付加し、missing mappingを隠さずcoverageとして測る最小moduleを作成した。
- Predictive evidence: なし。dataset未取得のためMAE改善claimは未検証。

## Limitations and Required Data

最低2、望ましくは5以上のbuilding/independent siteについて、IEQ timeseries、weather、occupancy、target ground truth、versioned semantic graphが必要である。sensor calibration、timezone、sampling、missingness、room/equipment mappingを確認する。occupant feedbackを使う場合はprivacyと倫理面の確認が必要である。

## Conclusion

研究課題は実証可能であるが、中心claimを支持する証拠はまだない。次の決定的stepは、timeseriesとsemantic modelがentity IDで結合できる複数building datasetを確保することである。data取得後、事前定義した三条件ablationとbuilding-held-out evaluationを実行する。

