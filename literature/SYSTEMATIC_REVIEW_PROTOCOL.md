# Systematic Literature Review Protocol

このprotocolは、研究テーマごとに再現可能なsystematic evidence mapを作り、研究gapを反証可能な形で特定するための正本である。PRISMA 2020、PRISMA-S、必要に応じてPRESSの考え方を採用する。「関連研究をすべて収集」は、事前宣言したdatabase、journal、期間、言語、document typeの範囲内での網羅的探索、citation chasing、更新検索として運用定義し、無限定な完全性は主張しない。

## Independent roles

| Role | Responsibility | Required output | Independence rule |
|---|---|---|---|
| Review Manager | protocol lock、scope、進行、PRISMA集計 | `protocol.json`, review status | screening票を上書きしない |
| Search Strategist | concept blocks、synonym、controlled vocabulary、DB別query | `search_log.csv` | Search Peer Reviewerと分離 |
| Search Peer Reviewer | PRESS型query査読、漏れ・過剰制限の検査 | query review記録 | query作成者と別pass |
| Database Harvester | bibliographic DB/API/indexからexport | `records.csv` | 採否判定をしない |
| Journal Harvester | seed journalとspecial issueを検索 | `records.csv`, coverage matrix | Impact Factorだけで除外しない |
| Citation Chaser | backward/forward citation、similar-article探索 | 追加search record | seed論文選定理由を記録 |
| Metadata Curator | DOI正規化、metadata補完、重複除去 | `records.csv` | relevanceで削除しない |
| Screener A / B | title/abstractとfull-textを独立判定 | `screening_decisions.csv` | 初回票を相互に見ない |
| Adjudicator | conflictをeligibility criteriaだけで解決 | adjudication row | 新criteriaを後付けしない |
| Quality Appraiser | study design別quality/risk-of-bias評価 | `extraction.csv` | 結果の好悪でscoreを変えない |
| Evidence Extractor | data、method、baseline、metric、結果、限界を抽出 | `extraction.csv` | 原文locationを付す |
| Gap Analyst | evidence matrix、矛盾、未検証条件、transfer riskを統合 | `LITERATURE.md` | 論文数の少なさだけをgapにしない |
| Review Auditor | coverage、dual screening、PRISMA count、DOI、除外理由を監査 | audit結果 | Review Managerと別pass |

同じAIが複数roleを逐次実行する場合も、入力、出力、判定を分離し、Screener Aの票を固定してからScreener Bを実行する。独立した人間または別agent実行が可能なら優先する。

## Review phases

1. `protocol.json`へRQ、review question、concept blocks、eligibility、sources、期間、言語、quality tool、synthesis planを記入し、検索前にlockする。
2. Search Strategistがdatabase別queryを作り、Search Peer Reviewerが既知のsentinel papersを回収できるか、重要概念の漏れ、不要な制限を査読する。
3. Database Harvesterは少なくともcitation index、domain database、open DOI/indexの相補的sourceを検索する。利用不能sourceはaccess limitationとして記録する。
4. Journal Harvesterは`journal_scope.json`のtopic-relevant seed journalを検索する。最新のJIF/quartileは実行時に公式JCRまたはpublisher/indexで確認し、取得年とsourceを記録する。
5. Metadata CuratorがDOIを正規化し、DOI、次いで正規化title/yearで重複候補を作る。曖昧候補は自動削除しない。
6. Screener A/Bがtitle/abstractを独立判定し、conflictをAdjudicatorが解決する。除外理由はcontrolled vocabularyを使う。
7. full textを取得可能な範囲で確認し、再び二重screeningする。未取得は除外と同一視せず`AWAITING_FULL_TEXT`とする。
8. Quality AppraiserとEvidence Extractorがstudy-design別に評価・抽出する。central claimに使うsourceは原文を確認する。
9. Citation Chaserがincluded studyと重要reviewからbackward/forward searchを行い、新規included studyが見つかればscreeningを反復する。
10. Gap Analystがtopic × context × data × method × comparator × outcome × validationのevidence matrixを作り、矛盾、未検証条件、再現性、外的妥当性を統合する。
11. Review Auditorがcoverage、PRISMA flow、二重判定、除外理由、metadata、query再現性、search updateを確認する。

## Mandatory coverage

- Bibliographic sources: Web of ScienceまたはScopus（利用可能時）、Engineering Village/Compendex、IEEE Xplore、ACM Digital Library、PubMed（IEQ/health）、TRID等からtopicに適合するもの。
- Open discovery: Crossref、OpenAlex、Semantic Scholar等。open indexだけを完全な代替とみなさない。
- Full-text retrieval: ユーザー確認済みの所属機関ScienceDirect accessをElsevier論文に優先利用する。認証状態は実行時に確認し、credentialや取得PDFをcommitしない。ScienceDirectをcross-publisher discoveryの唯一のsourceにしない。
- Domain sources: ASHRAE、CIBSE、IBPSA、buildingSMART、W3C、ISO等の公式standard/proceedings/specification。査読論文と区別する。
- Seed journals: `journal_scope.json`。対象誌は入口であり、検索の上限ではない。
- Citation search: included/critical papersのbackward、forward、related-article探索。
- Grey literature: dataset、technical report、thesis、preprintは目的を定義して補助利用し、査読済みevidenceと区別する。

必要なdatabase、API、connectorが利用可能または認証済みなら、RQとcoverageに寄与する範囲で実際に使用する。購読・認証・license等で利用不能なsourceは`NOT_ACCESSED`として理由を残し、同等の公開index、DOI metadata、repository、著者版を探索する。source名を計画へ書いただけで`SEARCHED`にしない。

## Eligibility and exclusion

研究ごとにPopulation/Context、Concept/Intervention/Exposure、Comparator、Outcome、study typeを明示する。少なくとも次を事前定義する。

- inclusion: topic relationship、building lifecycle phase、system/data type、outcome、publication type、date、language、peer-review status。
- exclusion reasons: `OUT_OF_SCOPE`, `WRONG_CONTEXT`, `WRONG_OUTCOME`, `WRONG_METHOD`, `WRONG_PUBLICATION_TYPE`, `NOT_PEER_REVIEWED`, `LANGUAGE`, `DATE_RANGE`, `NO_FULL_TEXT`, `DUPLICATE`, `RETRACTED`, `INSUFFICIENT_REPORTING`。
- `NO_FULL_TEXT`は取得努力とaccess limitationを記録した後だけ使用する。
- journal metric、positive result、citation countだけを除外理由にしない。

## Quality appraisal and synthesis

study designに応じてROB 2、ROBINS-I、QUADAS-2、CASP、JBI、PROBAST、または明示したdomain checklistを選ぶ。simulation、ML、building case studyにはdata leakage、train/test separation、baseline、ablation、uncertainty、external validation、climate/building transfer、sensor quality、semantic mappingを追加確認する。

gapは次に分類する。

- `EVIDENCE_GAP`: 対象条件のprimary evidenceがない。
- `CONTRADICTION_GAP`: 条件を揃えても結果が一致しない。
- `METHOD_GAP`: baseline、metric、validationまたは再現性が不十分。
- `DATA_GAP`: building type、climate、occupancy、sensor、semantic metadata等が欠ける。
- `TRANSFER_GAP`: building/site/domainを跨ぐ一般化が未検証。
- `IMPLEMENTATION_GAP`: 実験結果はあるが運用・費用・interoperabilityが未検証。
- `STANDARDIZATION_GAP`: schema、ontology、protocol、benchmarkが比較不能。

gap候補には支持source、反証source、検索coverage、gapを閉じる最小研究designを付ける。「未発見」を直ちに「不存在」と表現しない。

## Stop criteria

次をすべて満たすまでGate 1を通過しない。

- planned sourceとtopic-relevant seed journalの検索が完了し、query/date/result count/exportを記録した。
- title/abstractとfull-textの対象recordに二重判定または正当化された例外がある。
- conflictが解決され、full-text exclusion reasonが記録された。
- included/critical studyのbackward/forward citation searchが完了した。
- query更新またはcitation chasingを2 iteration行い、新規のgap-changing studyが見つからない、または飽和未達をlimitationとして明示した。
- contradictory/negative evidenceと隣接分野を検索した。
- PRISMA countがrecordsと整合し、最終検索日が報告されている。
- gapごとにevidence strength、反証可能性、最小検証designがある。

## Volume and result-cap policy

- 文献のretrieval、screening、eligibility、deep review、citationに固定の最大件数を設けない。
- database/UI/APIの先頭100件、1000件等の表示上限で探索を止めない。pagination、year split、query split、ISSN splitを使い、`result_count`と`export_count`を一致させる。
- corpusが大きい場合もscreening基準を狭めて件数だけを減らさず、protocol amendmentと再screening impactを記録する。
- deep reviewは`CRITICAL`、closest work、contradictory evidence、method/evaluation根拠を優先するが、eligible studyを無言で捨てない。
- default low-volume triggerはnon-niche topicでunique retrieval `<100`またはincluded primary study `<20`。発火時は検索漏れ監査を必須とし、niche topicとして妥当なら根拠とcoverage limitationを記録して解除する。
- report reference listには本文で使用した全sourceを含める。見かけの件数を増やすためだけの未使用citationは追加しない。

## Machine-readable artifacts

- `protocol.json`: review scopeと事前計画。
- `journal_scope.json`: domain別seed journalとmetric policy。
- `search_log.csv`: 実行した全query。
- `records.csv`: retrievalとdeduplicationのmaster record。
- `screening_decisions.csv`: reviewer別判定。
- `extraction.csv`: quality/evidence/gap抽出。`data_availability`列にはstudyが使用したdatasetの名称、DOI/URL、license、公開状態を記録し、data discoveryの`LITERATURE_DATA`探索に使う。
- `gaps.csv`: gap候補、支持/矛盾study、search coverage、最小closing design、Gap Challenger判定。
- `results/literature/prisma_flow.json`: flow count。

`code/literature/systematic_review.py`でdeduplication、flow集計、dual-screening auditを実行する。

Gate 1判定時は`audit`を`--allow-incomplete`なしで実行する。repository CIは進行中研究を許容するためstructureと既存rowの妥当性を検査し、研究完了性はGate checklistとstrict auditで判定する。

## Methodological references

- PRISMA 2020: https://www.prisma-statement.org/prisma-2020
- PRISMA-S: https://www.prisma-statement.org/prisma-search
- PRESS peer review guideline: https://pubmed.ncbi.nlm.nih.gov/27005575/
- Web of Science Core Collection: https://clarivate.com/academia-government/scientific-and-academic-research/research-discovery-and-referencing/web-of-science/web-of-science-core-collection/
- Scopus content coverage: https://www.elsevier.com/products/scopus/content
- Engineering Village / Compendex: https://www.elsevier.com/products/engineering-village/databases
- OpenAlex API: https://help.openalex.org/api/
- Crossref REST API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- DORA guidance on journal metrics: https://sfdora.org/read/
