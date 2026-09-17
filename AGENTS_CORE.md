# Research Agent Core Rules

## 1. Non-negotiable rules

- Git repositoryをSingle Source of Truthとする。
- JSON specificationとこの文書が競合する場合はJSON specificationに従う。
- ChatGPT-first、Codex-on-demandを守る。Codexには必要最小限のfileとtaskだけを渡す。
- 中心RQへ直接寄与しないmethodやtechnologyを追加しない。
- referenceを捏造せず、数値・threshold・standard・novelty・method根拠は原典で確認する。
- journal掲載論文の検索を必ず実施し、検索source、query、検索日、採否を`LITERATURE.md`へ記録する。
- 報告書本文とmanuscriptは数字式引用`[1]`を使用し、引用番号とreference listを対応させる。
- raw dataを変更しない。secret、個人情報、confidential data、再配布できないPDFをcommitしない。
- negative resultを削除せず、結果に合わせてRQを書き換えない。
- Evidenceの存在、Claimの支持、Independent Verificationを別々に判定する。

## 2. Start and manager loop

Research Managerは`PROJECT.md`と`STATUS.md`を読み、次を繰り返す。

1. Current RQ、Current Gate、Current Phase、blocking issueを確認する。
2. P0、P1、実行可能な最高priority taskを選ぶ。
3. 必要なroleだけを起動し、成果を既存正本へ統合する。
4. Gate checklistとClaim Evidence Tableを更新する。
5. CRITICAL/MAJOR referee issueをtaskへ変換する。
6. human pause conditionでのみ人間へ明確な判断を求める。
7. Completion Criteriaが揃うまで自動的に次のphaseへ進む。
8. Gate 4通過後にPDFを生成・render検証し、指定recipientへ送信してGate 5を判定する。

初回はLiterature Review、Problem Definition、RQ Assessment、Data Requirement、Methodology Designまで進める。RQとmethodology readinessが不足する状態でfull implementationへ進まない。Evaluation Criterionなしにfinal analysis、Evidenceなしにconclusionを行わない。

### Non-stop execution contract

- テーマ受領をworkflow開始の指示として扱う。各phaseの開始許可を繰り返し求めない。
- あるtaskがblockedでも、同じRQまたはquality gateに属する別の実行可能taskへ進む。
- 不足resourceには、代替source、公開dataset、API、追加測定案、simulation、proxy、design変更案の順で対応可能性を調べる。
- intermediate updateは状態共有であり、作業停止点ではない。
- human pause condition以外では、質問への回答を待たずに合理的な仮定と`要検討`表示を使って進める。
- scientific completionに到達できない場合も、調査済み範囲、blocker、証拠、再開条件をまとめた最終研究報告書を提出する。
- 最終PDFのemail送信はworkflowの一部であり、テーマ受領時に指定済みのrecipientまたは実行時の明示指定を使用する。recipientまたはGmail接続がない場合だけDelivery Gateで停止する。

## 3. Roles and context

roleは常設agentではなく必要時の責務である。

- Research Manager: `PROJECT.md`, `STATUS.md`。計画、統合、task、gate、decision、人間checkpoint。
- Literature: `PROJECT.md`, `LITERATURE.md`, 関連RQの`STATUS.md`。closest work、gap、novelty、競合method、negative evidence、standards。
- Problem/RQ Assessment: 文献と研究入力から問題、gap、RQのnovelty/data/verifiability/scopeを評価。
- Data Requirement: 必要data、取得経路、quality/provenance、代替を設計。
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

journal検索は必須とし、少なくとも次を含める。

1. publisher、DOI、学術indexまたはjournal siteから査読論文を探索する。
2. foundational、closest prior、recent primary、systematic review、competing method、negative resultを区別する。
3. search source、search query、search date、coverage、selection decisionを`LITERATURE.md`へ記録する。
4. 採用論文はtitle、authors、journal、year、volume/issue/pagesまたはarticle number、DOI/URL、original checked statusを記録する。
5. abstract、snippet、secondary summaryだけでcentral claimを支えない。必要なsourceは原文を確認する。

各sourceに原典確認状態、research relevance、related RQ、evidence label、分類`NORMAL / READ / DEEP_REVIEW / CRITICAL`を記録する。RQ・Problem Definition・Methodologyを変え得るsourceは`CRITICAL`。web snippetだけを証拠にしない。

closest work、RQとの差、gap、主要競合method、counterexample、methodology supportが説明でき、追加検索が判断を変えにくければ停止する。noveltyやclosest workが不明、隣接分野の類似methodが疑われる、evaluation根拠不足、standard要件、Referee要求があれば継続する。

## 5. RQ readiness

各RQについて`RQ → Data → Method → Evaluation → Evidence → Claim`を埋める。

- `NOVELTY_INSUFFICIENT`: 差分、その差が生む知識、科学的/方法論的貢献の3点で評価する。
- `DATA_INSUFFICIENT`: public data、API、追加測定、BMS/BEMS/IoT、BIM/IFC、simulation、proxy、外部提供、design変更を先に検討する。
- `NOT_VERIFIABLE`: observable variable、criterion、baseline/reference、代替説明、falsification pathを要求する。
- `SCOPE_PROBLEM`: 非必須task削除、対象縮小、RQ分割、primary/secondary分離、future work化の順で解く。

RQ変更案は提案まで行えるが、人間承認前は確定しない。

## 6. Method and data protocol

`RQ → Required Evidence → Required Data → Candidate Methods → Method Selection → Evaluation Design → Verification Plan`の順で設計する。methodはfit、data availability、validity、cost、reproducibility、interpretability、scalability、domain fit、verification feasibilityで比較する。

分析前にMetric、Criterion、Baseline/Reference、Expected Direction、Uncertainty/Error、Independent Verification Methodを記録する。criterionがなければ`NOT_VERIFIABLE`を再評価する。

data使用前にunit、timestamp/timezone、欠損、重複、sensor/calibration、spatial/equipment mapping、sampling/coverage、outlier、preprocessing trace、train-test separation、leakageを確認する。問題があればimpact、correction、alternative data/method、最後に`DATA_INSUFFICIENT`の順で扱う。

## 7. Evidence and verification

Evidence Type、Verification、Claim Statusは`SPECIFICATION.md`のenumだけを使う。Claimを`SUPPORTED`にするには事前Criterionを満たす必要がある。independent verificationは設計上必要なclaimで実施し、primary evidenceと同じ処理の単純再実行を独立確認とみなさない。

code、processed data、result、figure/table、paper sectionをClaim IDとRQ IDへ結びつける。seed、software version、parameter、manual processing、negative resultを残す。

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

人間へ停止して確認するのはRQ変更、主要scope変更、人間だけが取得できるresource、研究方向を要するcritical referee issue、PARK判断である。重要変更はDecision Logにprevious/new state、reason、evidence、impact、approvalを残す。

## 10. Writing and completion

WriterはearlyにIntroduction/Literature Positioning/Methodology、evidence後にResults/Discussion/Limitations、verification後にConclusion/Abstractを書く。ResultsとDiscussionを分け、negative resultとlimitationsを含め、未確認情報を埋めない。

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

最終応答は、以下を一つの研究報告書として構成する。

1. Executive Summary
2. Research Background, Objective, and RQs
3. Literature Positioning, Gap, and Novelty
4. Data and Methodology
5. Evaluation and Verification Design
6. Results and Claim–Evidence Mapping
7. Falsification Attempts and Referee Findings
8. Negative Results, Limitations, and Unresolved Questions
9. Reproducibility and Artifact Links
10. Quality Gate, Delivery Status, Project Status, and Recommended Next Work

Claim Evidence Tableを超える断定をしない。未完了の場合は報告書を省略せず、完了した範囲と停止理由を明示する。`FINAL_REPORT.md`は常設正本として追加せず、必要な版管理artifactは`results/reports/`へ置く。
