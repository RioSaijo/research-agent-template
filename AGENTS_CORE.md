# Research Agent Core Rules

## 1. Non-negotiable rules

- Git repositoryをSingle Source of Truthとする。
- JSON specificationとこの文書が競合する場合はJSON specificationに従う。
- ChatGPT-first、Codex-on-demandを守る。Codexには必要最小限のfileとtaskだけを渡す。
- 中心RQへ直接寄与しないmethodやtechnologyを追加しない。
- referenceを捏造せず、数値・threshold・standard・novelty・method根拠は原典で確認する。
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

初回はLiterature Review、Problem Definition、RQ Assessment、Data Requirement、Methodology Designまで進める。RQとmethodology readinessが不足する状態でfull implementationへ進まない。Evaluation Criterionなしにfinal analysis、Evidenceなしにconclusionを行わない。

## 3. Roles and context

roleは常設agentではなく必要時の責務である。

- Research Manager: `PROJECT.md`, `STATUS.md`。計画、統合、task、gate、decision、人間checkpoint。
- Literature: `PROJECT.md`, `LITERATURE.md`, 関連RQの`STATUS.md`。closest work、gap、novelty、競合method、negative evidence、standards。
- Problem/RQ Assessment: 文献と研究入力から問題、gap、RQのnovelty/data/verifiability/scopeを評価。
- Data Requirement: 必要data、取得経路、quality/provenance、代替を設計。
- Methodology/Analysis: `PROJECT.md`, `STATUS.md`, 関連artifact。RQから必要証拠を逆算し、method/evaluation/verificationを設計・実行。
- Specialist: RQ、method、data、evaluationが専門知識を必要とする場合だけ起動。結果は既存正本へ統合し、研究scopeを独立に拡張しない。
- Verification: criterion適用、再現性、代替説明、必要な独立確認。
- Referee: conversationや自己評価ではなくartifactを読む。反証を先に試す。
- Writer: `PROJECT.md`, `STATUS.md`, `LITERATURE.md`, 関連manuscript。Claim Evidenceを上限として段階的に書く。

## 4. Literature protocol

foundational、closest prior、recent primary、systematic review、competing methods、negative/contradictory results、limitations、benchmark、standards/regulations、adjacent fieldsを検索する。

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
5. CRITICAL/MAJORを`STATUS.md`のtaskへ変換し、revision後のartifactから再確認する。

Refereeは中心claimを肯定することを目的にしない。独立検証は全研究で機械的に必須化せず、claim riskとdesignに応じて評価する。

## 9. Quality gates and human pauses

Gate checklistは`STATUS.md`で管理する。Gate失敗を隠して先へ進まない。

人間へ停止して確認するのはRQ変更、主要scope変更、人間だけが取得できるresource、研究方向を要するcritical referee issue、PARK判断である。重要変更はDecision Logにprevious/new state、reason、evidence、impact、approvalを残す。

## 10. Writing and completion

WriterはearlyにIntroduction/Literature Positioning/Methodology、evidence後にResults/Discussion/Limitations、verification後にConclusion/Abstractを書く。ResultsとDiscussionを分け、negative resultとlimitationsを含め、未確認情報を埋めない。

Gate 4と`SPECIFICATION.md`のCompletion Criteriaを満たし、Referee decisionがPASSで、未解決CRITICALがない時だけ`PROJECT_STATUS: COMPLETE`にする。最終成果には4正本、reproducible code（該当時）、results、Claim Evidence mapping、manuscript、reference、limitations、unresolved questionsを含める。

