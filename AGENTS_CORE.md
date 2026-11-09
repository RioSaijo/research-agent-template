# Research Agent Core Rules

## 1. Non-negotiable rules

- Git repositoryをSingle Source of Truthとする。
- JSON specificationとこの文書が競合する場合はJSON specificationに従う。
- platform-neutralに運用し、ChatGPT、Claude Code、Codex等を併用可能に保つ。role定義は`agents/roles.json`を正本とし、生成された`agents/portable/`または`.claude/agents/`を使う。各agentには必要最小限のfileとtaskだけを渡す。
- 中心RQへ直接寄与しないmethodやtechnologyを追加しない。
- referenceを捏造せず、数値・threshold・standard・novelty・method根拠は原典で確認する。
- journal掲載論文の検索を必ず実施し、検索source、query、検索日、採否を`LITERATURE.md`へ記録する。
- 文献検索は`literature/SYSTEMATIC_REVIEW_PROTOCOL.md`に従い、single-agent narrative searchだけでGate 1を通過しない。
- 報告書本文とmanuscriptは数字式引用`[1]`を使用し、引用番号とreference listを対応させる。
- raw dataを変更しない。secret、個人情報、confidential data、再配布できないPDFをcommitしない。
- negative resultを削除せず、結果に合わせてRQを書き換えない。
- Evidenceの存在、Claimの支持、Independent Verificationを別々に判定する。

## 2. Start and manager loop

Research Managerは`PROJECT.md`と`STATUS.md`を読み、次を繰り返す。

0. `inputs/intake.json`のstageとrouteを確認する。未判定ならIntake Coordinatorを起動してbriefと添付資料を登録させ、成熟度（S0〜S4）に応じた開始点を決める（`SPECIFICATION.md` 4）。S0/S1ではExploration Analystの選択肢を人間に提示し、選択を待つ。
1. Current RQ、Current Gate、Current Phase、blocking issueを確認する。
2. P0、P1、実行可能な最高priority taskを選ぶ。
3. 必要なroleだけを起動し、成果を既存正本へ統合する。
4. Gate checklistとClaim Evidence Tableを更新する。
5. CRITICAL/MAJOR referee issueをtaskへ変換する。
6. human pause conditionでのみ人間へ明確な判断を求める。
7. Completion Criteriaが揃うまで自動的に次のphaseへ進む。
8. Gate 4通過後にPDFを生成・render検証し、指定recipientへ送信してGate 5を判定する。

S2以降の初回はLiterature Review、Problem Definition、RQ Assessment、Data Requirement、Methodology Designまで進める。RQとmethodology readinessが不足する状態でfull implementationへ進まない。Evaluation Criterionなしにfinal analysis、Evidenceなしにconclusionを行わない。

### Non-stop execution contract

- テーマ受領をworkflow開始の指示として扱う。各phaseの開始許可を繰り返し求めない。
- あるtaskがblockedでも、同じRQまたはquality gateに属する別の実行可能taskへ進む。
- 不足resourceには、代替source、公開dataset、API、追加測定案、simulation・synthetic等の生成data（必ず生成dataと明示）、proxy、design変更案の順で対応可能性を調べる。
- intermediate updateは状態共有であり、作業停止点ではない。
- human pause condition以外では、質問への回答を待たずに合理的な仮定と`要検討`表示を使って進める。
- scientific completionに到達できない場合も、調査済み範囲、blocker、証拠、再開条件をまとめた最終研究報告書を提出する。
- 最終PDFのemail送信はworkflowの一部であり、テーマ受領時に指定済みのrecipientまたは実行時の明示指定を使用する。recipientまたはGmail接続がない場合だけDelivery Gateで停止する。

## 3. Roles and context

roleは常設agentではなく必要時の責務である。各roleの入力、出力、独立性、手順、停止条件は`agents/roles.json`が正本であり、どのplatformでも同じ定義から起動する（`SPECIFICATION.md` 2）。下記は概要である。

- Research Manager: `PROJECT.md`, `STATUS.md`。計画、統合、task、gate、decision、人間checkpoint。
- Intake Coordinator: 研究briefと添付資料の登録・振り分け、成熟度（S0〜S4）の判定、開始点と人間の判断点の記録。
- Exploration Analyst: S0/S1で予備調査を行い、問題とRQの選択肢を根拠付きで示す。選択はしない。
- Literature: `PROJECT.md`, `LITERATURE.md`, 関連RQの`STATUS.md`。closest work、gap、novelty、競合method、negative evidence、standards。
- Review Protocol Lead: review question、eligibility、source、期間、quality、synthesis、停止条件を検索前に固定する。
- Domain Vocabulary / Search Strategist: 建築設備、建築情報、エネルギーのconcept block、同義語、controlled vocabulary、database別queryを作る。
- Search Peer Reviewer: query作成者と分離し、既知paper recall、Boolean、field、filter、表記揺れ、不要な制限を査読する。
- Database / Journal Harvester: database、index、publisher、seed journalから全retrievalとsearch provenanceを保存する。
- Metadata Curator: DOI、title、year、authorを正規化し、duplicateとrelated reportを追跡可能に統合する。
- Screener A / B: title/abstractとfull textを相互の初回票を見ずに判定する。情報不足を自動除外しない。
- Eligibility Adjudicator: disagreementだけを事前eligibilityで解決し、full-text exclusion reasonを記録する。
- Quality Appraiser / Evidence Extractor: study-design別risk、data、method、baseline、metric、result、uncertainty、limitation、source locationを抽出する。
- Citation Chaser: critical/included studyのbackward/forward searchを反復し、追加収量を記録する。
- Gap Analyst / Gap Challenger: evidence matrixからgap候補を作り、用語漏れ、隣接分野、contradiction、既存研究でgapが消えないか別passで反証する。
- Review Auditor: dual screening、coverage、PRISMA count、metadata、除外、quality、gap traceabilityを独立監査する。
- Problem/RQ Assessment: 文献と研究入力から問題、gap、RQのnovelty/data/verifiability/scopeを評価。
- Data Requirement: RQ、gap、analysis planから必要evidenceと変数・解像度・coverage・品質要件を逆算し`data/requirements.csv`へ記録する。
- Data Source Scout: requirementごとにpublic data、literature data、API、measurement/BMS/BIM、simulation、proxy、external provider、design changeのpathwayを探索し`data/source_search_log.csv`へ記録する。
- Data Screener: candidate datasetを`data/screening_rubric.json`のanchorに従いfit、coverage、resolution、quality、access、cost、reproducibilityで0-3評価し、anchorを引用したrationaleと選定・却下理由を`data/candidates.csv`へ記録する。Data Source Scoutと別passで行い、MUST requirementの選定は別roleが再採点する。
- Methodology/Analysis: `PROJECT.md`, `STATUS.md`, 関連artifact。RQから必要証拠を逆算し、method/evaluation/verificationを設計・実行。
- Specialist: RQ、method、data、evaluationが専門知識を必要とする場合だけ起動。結果は既存正本へ統合し、研究scopeを独立に拡張しない。
- Evidence Auditor: central claimごとに原典、data provenance、数値、引用、Claim–Evidenceの到達可能性を監査する。
- Methods Challenger: baseline、ablation、leakage、bias、交絡、感度分析、外的妥当性、代替methodを敵対的に検討する。Methodology/Analysisと同じ自己評価を再利用しない。
- Reproducibility Auditor: code、parameter、seed、environment、data transformation、figure/table生成経路から再現可能性を独立に確認する。
- Verification: criterion適用、再現性、代替説明、必要な独立確認。
- Referee: conversationや自己評価ではなくartifactを読む。反証を先に試す。
- Revision Lead: Referee issueごとに原因を診断し、複数の解決候補を比較してresponse案と修正taskを作る。Referee自身は兼任しない。
- Writer: `PROJECT.md`, `STATUS.md`, `LITERATURE.md`, 関連manuscript。Claim Evidenceを上限として段階的に書く。

追加roleは人数を増やすこと自体を目的にせず、central claimのriskに応じて起動する。少なくとも中心claimにはLiterature、Methods Challenger、Evidence AuditorまたはVerification、Referee、Revision Leadの相互に区別された視点を適用する。各roleは入力artifact、問い、出力、停止条件を明示し、結果を正本へ統合する。

## 4. Literature protocol

foundational、closest prior、recent primary、systematic review、competing methods、negative/contradictory results、limitations、benchmark、standards/regulations、adjacent fieldsを検索する。

最初に`literature/protocol.json`をtopicへ適合させ、search前にlockする。Search StrategistのqueryはSearch Peer Reviewerが確認し、Database/Journal Harvesterは`search_log.csv`へ完全なquery、platform、date、coverage、filter、hit/export件数を保存する。topic-relevantな`journal_scope.json`のseed journalをすべてcoverage matrixへ入れ、database検索、journal sweep、backward/forward citation chasingを相補的に用いる。

Metadata Curatorはretrieval rowを削除せずcanonical recordへ関連付ける。Screener A/Bはtitle/abstractとfull textを独立判定し、Adjudicatorが不一致だけを処理する。同一roleの即時再読をdual screeningとみなさない。included studyはquality appraisalとevidence extractionを完了し、Gap Analystの候補をGap Challengerが反証してからgapとして採用する。Review AuditorはPRISMA countとrecordを照合する。

高JIF/Q1 journalは探索順序を優先できるが、metricは毎年変わるため年と公式sourceを記録し、eligibility除外条件には使わない。専門誌、conference、negative result、lower-metric journalにclosest workがあれば含める。

journal検索は必須とし、少なくとも次を含める。

1. publisher、DOI、学術indexまたはjournal siteから査読論文を探索する。
2. foundational、closest prior、recent primary、systematic review、competing method、negative resultを区別する。
3. search source、search query、search date、coverage、selection decisionを`LITERATURE.md`へ記録する。
4. 採用論文はtitle、authors、journal、year、volume/issue/pagesまたはarticle number、DOI/URL、original checked statusを記録する。
5. abstract、snippet、secondary summaryだけでcentral claimを支えない。必要なsourceは原文を確認する。

各sourceに原典確認状態、research relevance、related RQ、evidence label、分類`NORMAL / READ / DEEP_REVIEW / CRITICAL`を記録する。RQ・Problem Definition・Methodologyを変え得るsourceは`CRITICAL`。web snippetだけを証拠にしない。

planned sourceとseed journalの検索、query review、重複処理、二重screening、conflict解消、quality/extraction、citation chasing、contradictory evidence探索、PRISMA整合、gap challengeが完了し、連続2回のsearch/citation waveでgapを変えるstudyが見つからなければLiterature Sub-gateを判定できる。満たさない場合はcoverage limitationを明記し、無限定な網羅性を主張しない。noveltyやclosest workが不明、隣接分野の類似methodが疑われる、evaluation根拠不足、standard要件、Referee要求があれば継続する。

## 5. RQ readiness

各RQについて`RQ → Data → Method → Evaluation → Evidence → Claim`を埋める。

- `NOVELTY_INSUFFICIENT`: 差分、その差が生む知識、科学的/方法論的貢献の3点で評価する。
- `DATA_INSUFFICIENT`: public data、API、追加測定、BMS/BEMS/IoT、BIM/IFC、simulation、proxy、外部提供、design変更を先に検討する。
- `NOT_VERIFIABLE`: observable variable、criterion、baseline/reference、代替説明、falsification pathを要求する。
- `SCOPE_PROBLEM`: 非必須task削除、対象縮小、RQ分割、primary/secondary分離、future work化の順で解く。

RQ変更案は提案まで行えるが、人間承認前は確定しない。

### Problem-to-data chain

`Problem → Gap → RQ → Data Requirement → Search → Candidate → Manifest → Quality`を`SPECIFICATION.md` 6.1に従って記録し、`python code/data/discovery.py audit`で検査する。

1. Gap Analystが`literature/gaps.csv`へgap候補を書き、Gap Challengerが別passでcounter-searchして判定する。支持studyはextraction済みでなければならない。
2. RQ表のGap IDs列にaccepted gapを記入する。gapが棄却されたRQは人間判断へ送る。
3. Data Requirement roleがgap type、metric、criterion、baselineからrequirementを逆算する。
4. Data Source Scoutが`discovery.py search`とconnector/web/APIでpathwayを探索する。included studyの`data_availability`を必ず追う。
5. Data Screenerがcandidateを採点・選定し、選定dataを`acquire.py`で取得、`quality.py`で検査する。
6. `discovery.py matrix`でchainを出力し、Gate 2で`--allow-incomplete`なしのauditを通す。

## 6. Method and data protocol

`RQ → Required Evidence → Required Data → Candidate Methods → Method Selection → Evaluation Design → Verification Plan`の順で設計する。methodはfit、data availability、validity、cost、reproducibility、interpretability、scalability、domain fit、verification feasibilityで比較する。

分析前にMetric、Criterion、Baseline/Reference、Expected Direction、Uncertainty/Error、Independent Verification Methodを記録する。criterionがなければ`NOT_VERIFIABLE`を再評価する。

data使用前にunit、timestamp/timezone、欠損、重複、sensor/calibration、spatial/equipment mapping、sampling/coverage、outlier、preprocessing trace、train-test separation、leakageを確認する。問題があればimpact、correction、alternative data/method、最後に`DATA_INSUFFICIENT`の順で扱う。

### Data and analysis toolkit

1. Data Requirement roleは`data/manifest.json`へdataset entry（source、owner、access、license、variable、unit、valid range、timestamp column、timezone、expected interval）を作り、`python code/data/acquire.py fetch|register`で取得・登録する。raw dataは`data/raw/`でread-onlyとし、commitしない。
2. 使用前に`python code/data/quality.py profile --data-id <ID> --record-check <CHECK-ID> --claim-id <CL>`を実行する。WARN/FAILは補正、除外、代替dataのいずれかとその影響を記録する。
3. Analysis roleは`code/analysis/stats.py`の共通metric、bootstrap、比較検定、multiplicity補正、rolling-origin splitを使い、閾値はanalysis planから読む。
4. confirmatory runは`python code/analysis/record_run.py ... -- <command>`で実行し、手でruns.csvを書かない。
5. Gate 3前に`python code/data/acquire.py verify`（raw dataのあるenvironmentで）とstrict evidence auditを実行する。
6. 全collection pathwayで取得できないdataは、`SPECIFICATION.md` 7.3に従い生成して検証・活用できる。Data Generatorがfidelity基準を先に固定して`code/data/generate.py`で登録し、別roleのGenerated Data Validatorが検証する。生成dataであることはmanifest、file行、sidecar、runs、claims、STATUS.md、原稿（`\GeneratedData{ID}`）、PDFのすべてで明示し、observed dataとして記述しない。

## 7. Evidence and verification

Evidence Type、Verification、Claim Statusは`SPECIFICATION.md`のenumだけを使う。Claimを`SUPPORTED`にするには事前Criterionを満たす必要がある。independent verificationは設計上必要なclaimで実施し、primary evidenceと同じ処理の単純再実行を独立確認とみなさない。

code、processed data、result、figure/table、paper sectionをClaim IDとRQ IDへ結びつける。seed、software version、parameter、manual processing、negative resultを残す。

### Gate 3 evidence control

`evidence/`をGate 3のmachine-readable正本とし、`STATUS.md`のClaim Evidence Tableはその要約として一致させる。

1. Methodology roleはconfirmatory runの前に`evidence/analysis_plan.json`をlockする。各analysisにclaim ID、claim type（`DESCRIPTIVE / ASSOCIATIONAL / CAUSAL / PREDICTIVE / COMPARATIVE / GENERALIZATION / FEASIBILITY`）、metric、数値またはMANUAL criterion、baseline、expected direction、uncertainty method、required check、verification independence levelを固定する。lock後の変更はamendmentとして旧値、新値、理由、再分析要否を残す。
2. Analysis roleはすべての実行を`evidence/runs.csv`へ記録する（run type、role、時刻、git commit、command、environment、seed、input/output pathとSHA-256）。lock前のrunは`EXPLORATORY`だけとし、confirmatory evidenceに使わない。
3. Methods ChallengerとVerificationは`evidence/checks.csv`へcheckを記録する。`ALTERNATIVE_EXPLANATION`、`FALSIFICATION`、`NEGATIVE_CONTROL`、`INDEPENDENT_VERIFICATION`はprimary analystと別roleが行う。
4. claim typeごとの最低checkはplanから削除できない。DATA_QUALITYは常に、central claimはALTERNATIVE_EXPLANATIONとSENSITIVITY、CAUSALはFALSIFICATION、PREDICTIVEはLEAKAGEとBASELINE、COMPARATIVEはBASELINE、GENERALIZATIONはTRANSFERを要する。
5. independence levelは`NONE < RERUN < ALTERNATIVE_METHOD < INDEPENDENT_IMPLEMENTATION < INDEPENDENT_DATA < EXTERNAL`とする。RERUNとALTERNATIVE_METHODは`INTERNALLY_VERIFIED`まで、`INDEPENDENTLY_VERIFIED`には別roleによるINDEPENDENT_IMPLEMENTATION以上を要する。
6. Evidence Auditorは`python code/evidence/evidence_audit.py report --status STATUS.md --verify-files`を`--allow-incomplete`なしで実行し、全issueを解消するか、claimを縮小・`PARTIALLY_SUPPORTED`・`UNSUPPORTED`へ下げる。pre-registerされていないclaimは`PRELIMINARY`を上限とし、negative resultを`claims.csv`から削除しない。

## 8. Referee protocol

Topic Review、Scientific and Technical Review、Publication Readiness Reviewを行う。各roundは次の順にする。

1. 対象Claimとartifactを特定する。
2. 反例、data leakage、bias、artifact、assumption dependence、alternative explanation、literature conflict、novelty overclaim、falsification failureを探す。
3. 反証試行に耐えた範囲だけvalidationする。
4. issueにseverityと必要revisionを付ける。
5. CRITICAL/MAJORを`STATUS.md`のtaskへ変換する。
6. Revision Leadが各issueについて、査読指摘の要約、根本原因、`ACCEPT / PARTIAL / DISAGREE`、検討した解決候補、選択した解決策と理由、具体的action、変更対象、必要証拠、残存riskを`REFEREE.md`のResponse to Refereeへ記録する。
7. 修正を実行し、responseへartifact、結果、manuscriptの変更箇所を対応付ける。反論する場合も根拠を提示し、指摘を黙って却下しない。
8. 元のReferee roleがrevision後のartifactだけから再査読し、各issueを`ACCEPTED / PARTIALLY_ACCEPTED / REJECTED / SUPERSEDED`で判定する。Revision Leadの自己判定だけでCLOSEDにしない。
9. `REJECTED`または未解決CRITICAL/MAJORがあれば、解決案の再設計、追加分析、追加文献探索、claim縮小のいずれかを行い、次roundへ進む。

Refereeは中心claimを肯定することを目的にしない。独立検証は全研究で機械的に必須化せず、claim riskとdesignに応じて評価する。

修正ループは`issue → diagnosis → solution alternatives → response → revision → new evidence → independent re-review → disposition`である。文章だけを直して科学的な指摘を解決済みにしてはならない。各roundで解決しなかった理由と研究判断への影響を残す。

## 9. Quality gates and human pauses

Gate checklistは`STATUS.md`で管理する。Gate失敗を隠して先へ進まない。

人間へ停止して確認するのはS0/S1の選択肢の選択、RQ変更、主要scope変更、人間だけが取得できるresource、研究方向を要するcritical referee issue、PARK判断である。重要変更はDecision Logにprevious/new state、reason、evidence、impact、approvalを残す。

## 10. Writing and completion

Writerは固定outlineを流用せず、研究type、結果、evidence量、読者、publication targetに応じてoutlineと分量を設計する。結果と解釈はheadingを分けるか本文内で明確に区別し、negative resultとlimitationsを含め、未確認情報を埋めない。該当しない章を水増しせず、必要な論証には十分な深さを与える。

本文引用は数字式`[1]`とし、LaTeXでは`\cite{...}`と`unsrt` bibliographyを用いて初出順の番号を生成する。referenceのない事実・数値・先行研究比較を残さない。

Gate 4とGate 5、`SPECIFICATION.md`のCompletion Criteriaを満たし、Referee decisionがPASSで、未解決CRITICALがない時だけ`PROJECT_STATUS: COMPLETE`にする。最終成果には4正本、reproducible code（該当時）、results、Claim Evidence mapping、manuscript、reference、limitations、unresolved questions、検証済みPDF、delivery recordを含める。

### PDF and email delivery

1. `results/reports/`へ最終PDFを生成する。
2. 全pageをrenderし、文字化け、clipping、overlap、表・図・引用番号・reference listを目視または画像検査する。
3. Gmail connectorの認証accountとrecipientを確認する。recipientやcredentialをrepositoryへcommitしない。
4. PDFを添付し、研究テーマを識別できるsubjectと短いsummaryを付けて送信する。
5. Gmail responseで送信成功を確認する。
6. `STATUS.md`にPDF path、recipient source、sent timestamp、message ID、delivery statusを記録する。email address、token、session情報は記録しない。
7. 送信失敗時は`PROJECT_STATUS: COMPLETE`にせず、原因と再送条件を記録する。

### Final research report

最終応答は一つの研究報告書として構成するが、固定された章名、順序、項目数、word/page数を要求しない。Writerは`PROJECT.md`のReport Designに従い、研究結果を最も正確に伝える構成を選ぶ。

構造にかかわらず、problem/RQ、systematic literature coverage、gap、data/source、method、evaluation、results、Claim–Evidence、反証・代替説明、Referee findings/response、negative results、limitations、未解決事項、再現性、artifact link、quality gate、delivery/project statusのうち該当する内容を追跡可能にする。該当しない内容は省略でき、密接な内容は統合できる。

Claim Evidence Tableを超える断定をしない。未完了の場合は報告書を省略せず、完了した範囲と停止理由を明示する。`FINAL_REPORT.md`は常設正本として追加せず、必要な版管理artifactは`results/reports/`へ置く。
