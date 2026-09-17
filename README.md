# research-agent-template

既に定義された研究テーマを、計画、文献調査、実装、検証、査読、執筆まで一貫して管理するための再利用可能な研究環境です。建築設備・建築環境、BMS/BEMS/BAS、IoT、BIM/IFC、データ工学、統計・機械学習、デジタルツイン、施設管理などを含む横断研究を想定しますが、単一分野や特定技術に固定しません。

## 運用原則

- Git repositoryを唯一の正本とし、会話履歴に研究状態を依存させません。
- ChatGPTが研究判断と管理を担当し、Codexはrepository-wideな実装等が必要な場合だけ使います。
- Research Question (RQ) をData、Method、Evaluation、Evidence、Claimへ追跡します。
- 評価基準を分析前に定義し、証拠の存在と主張の支持を区別します。
- Refereeは確認より先に反証可能性、代替説明、データ品質問題を探します。
- 各CRITICAL/MAJOR査読指摘に対し、Revision Leadが複数の解決候補、採用理由、具体的修正、追加証拠、残存リスクをResponse to Refereeとして提示し、Refereeが独立に再査読します。
- 中心claimにはLiterature、Methods Challenger、Evidence Auditor、Reproducibility Auditor、Refereeなど異なる視点をriskに応じて割り当て、単なるagent数ではなく検討の非重複性で研究の深度を確保します。
- 文献レビューはPRISMA 2020/PRISMA-S/PRESSを参照し、protocol事前固定、複数databaseとseed journal、独立二重screening、quality appraisal、citation chasing、Gap Challenger、Review Auditorに分離します。
- `Energy and Buildings`等の高impact誌を優先探索しますが、Impact Factorは年次更新される探索属性として記録し、個別論文の除外基準にはしません。
- RQ、中心的問題、主要scope、中心的貢献の変更には人間の承認が必要です。

## 開始方法

1. 研究テーマをChatGPTへ送ります。背景、目的、RQが不完全でも開始できます。不明な項目は推測せず `要検討` とします。
2. ChatGPTは`AGENTS.md`を入口として、systematic review protocol、検索式査読、文献収集、二重screening、quality/gap分析、問題定義、RQ評価、データ要件、方法設計、分析、検証、査読、引用番号付き執筆を自動的に進めます。
3. `STATUS.md`で現在のphase、quality gate、task、Claim Evidence Tableを確認します。
4. 重要な研究方針変更や人間だけが取得できる資源が必要になった場合に限り、人間が判断します。
5. Gate 4通過後、最終PDFを生成・render検証し、Gmailで指定recipientへ送信します。送信記録までが一連のworkflowです。

## Non-stop execution and final report

テーマ受領後は、通常の途中確認やphaseごとの承認を求めず、実行可能なtaskを継続して処理します。情報不足があっても、文献・公開data・simulation・代替methodなど、仕様で許された経路を先に調べます。

中断するのは、RQ変更、主要scope変更、人間だけが取得できるresource、研究方向の判断を要するCRITICAL issue、PARK判断など、仕様上人間の承認が必要な場合だけです。

終了時は、単なる進捗通知ではなく、次を含む研究報告書をchatで提出します。

- 研究課題、背景、目的、RQ
- 文献positioning、closest prior work、research gap、novelty評価
- data、method、evaluation criterion、verification design
- 実施内容、結果、negative result、Claim–Evidence対応
- Referee findings、limitations、unresolved questions
- quality gateとcompletion criteriaの状態
- reproducibility情報と成果物へのlink
- 本文中の数字式引用`[1]`と検証済みreference list
- PDF render QAとGmail delivery status

`FINAL_REPORT.md`は常設せず、Git repositoryの正本から最終応答として生成します。研究内容に応じて必要な場合は、`results/reports/`へ版管理可能な報告書artifactを作成できます。

## Multiple research projects

このrepository自体には個別研究のdata、文献、結果を保存しません。新しい研究テーマごとに、このtemplateから`research-<topic-slug>`という独立repositoryを作成します。

- 1 research project = 1 Git repository
- repositoryごとに`PROJECT.md`、`STATUS.md`、文献、data provenance、code、results、paperを分離
- 全projectの一覧と最終報告書linkは`research-project-index`で管理
- 完了projectは成果物を維持したままGitHubでarchive可能

これにより、研究テーマ間でdata、dependency、Claim–Evidence、Git履歴、CI、PDFが混在することを防ぎます。

## 構成

```text
research-agent-template/
├── README.md
├── SPECIFICATION.md
├── AGENTS.md
├── AGENTS_CORE.md
├── PROJECT.md
├── STATUS.md
├── LITERATURE.md
├── REFEREE.md
├── literature/
│   ├── SYSTEMATIC_REVIEW_PROTOCOL.md
│   ├── protocol.json
│   ├── journal_scope.json
│   ├── search_log.csv
│   ├── records.csv
│   ├── screening_decisions.csv
│   └── extraction.csv
├── paper/
│   ├── main.tex
│   ├── refs.bib
│   └── figures/
├── code/
│   └── literature/systematic_review.py
├── results/
├── tests/
├── scripts/check.sh
└── .github/workflows/ci.yml
```

`code/`と`results/`の下位directoryは必要になった時だけ作ります。生データは原則Git管理せず、read-onlyとして扱い、入手元と処理履歴を`PROJECT.md`および成果物に記録します。

## 5つのquality gate

1. Research Definition Gate
2. Methodology Readiness Gate
3. Evidence and Verification Gate
4. Publication Readiness Gate
5. Report Delivery Gate

研究完了は論文の文章量ではなく、問題定義、新規性、方法、評価基準、証拠、検証、査読、再現性、引用番号付きPDF、メール送信記録が揃ったことで判断します。
