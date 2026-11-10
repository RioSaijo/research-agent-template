# research-agent-template

既に定義された研究テーマを、計画、文献調査、実装、検証、査読、執筆まで一貫して管理するための再利用可能な研究環境です。建築設備・建築環境、BMS/BEMS/BAS、IoT、BIM/IFC、データ工学、統計・機械学習、デジタルツイン、施設管理などを含む横断研究を想定しますが、単一分野や特定技術に固定しません。

## 運用原則

- Git repositoryを唯一の正本とし、会話履歴に研究状態を依存させません。
- ChatGPT、Claude Code、Codexなどを併用できます。role定義は`agents/roles.json`を唯一の正本とし、各platform用のagent fileはそこから生成します。
- Research Question (RQ) をData、Method、Evaluation、Evidence、Claimへ追跡します。
- 評価基準を分析前に定義し、証拠の存在と主張の支持を区別します。
- Refereeは確認より先に反証可能性、代替説明、データ品質問題を探します。
- 各CRITICAL/MAJOR査読指摘に対し、Revision Leadが複数の解決候補、採用理由、具体的修正、追加証拠、残存リスクをResponse to Refereeとして提示し、Refereeが独立に再査読します。
- 中心claimにはLiterature、Methods Challenger、Evidence Auditor、Reproducibility Auditor、Refereeなど異なる視点をriskに応じて割り当て、単なるagent数ではなく検討の非重複性で研究の深度を確保します。
- 文献レビューはPRISMA 2020/PRISMA-S/PRESSを参照し、protocol事前固定、複数databaseとseed journal、独立二重screening、quality appraisal、citation chasing、Gap Challenger、Review Auditorに分離します。
- `Energy and Buildings`等の高impact誌を優先探索しますが、Impact Factorは年次更新される探索属性として記録し、個別論文の除外基準にはしません。
- 報告書は固定章立てや固定分量に依存せず、研究type、結果、evidence量、読者、target venueからoutlineと長さを決めます。必須なのは内容の追跡可能性です。
- RQに必要な学術database、公式API、標準、dataset、repository、認証済みconnectorは利用可能性に応じて使用し、アクセス不能なsourceとcoverageへの影響を明記します。
- ユーザー確認済みの所属機関ScienceDirect accessをElsevier論文の原文確認に優先利用し、他publisherの研究は複数database/indexで補完します。認証情報やライセンスPDFはrepositoryへ保存しません。
- RQ、中心的問題、主要scope、中心的貢献の変更には人間の承認が必要です。

## 開始方法

アイデアの段階は問いません。関心領域だけ（S0）でも、問題意識（S1）、RQ案（S2）、設計済み（S3）、既存の原稿や査読コメントがある継続・改訂（S4）でも開始できます。Intake Coordinatorが段階を判定し、S0/S1では予備調査で研究の方向の選択肢を示して、あなたの選択を待ちます。

### 依頼の書き方（必須は1行目だけ）

```
■ やりたいこと：（1〜3文。漠然としていてよい）
■ きっかけ・背景：
■ 仮の問い・仮説：（あれば）
■ 欲しい成果：論文 / 報告書 / 提案書 / 卒論・修論 / 方針判断の材料
■ 制約：期間、使えるデータ・計測、計算資源、予算
■ 手持ちの資料：（添付の一覧と、それぞれ何のための資料か）
■ 範囲外にしたいこと：
■ 締切・投稿先：
```

研究の進め方の規則（独立判定、引用形式など）はrepositoryにあるので、依頼に書く必要はありません。送付先のemailは実行時に伝え、repositoryには記録しません。

### 添付資料

| 添付の種類 | 行き先 | 扱い |
|---|---|---|
| 論文PDF、文献リスト（.bib/.ris） | `literature/records.csv` | ユーザー提供として記録。screeningは免除せず、検索式の回収確認と引用追跡の起点に使う |
| データ（CSV、Excel、BMS出力）、図面・IFC | `data/manifest.json`、data候補 | 観測dataとして登録し、他の候補と同じく採点・品質検査 |
| 自分の原稿・研究計画書 | `PROJECT.md` | 「ユーザー記載・未検証」として転記。主張は検証まで根拠にしない |
| 査読コメント | `REFEREE.md` | 外部査読の指摘として登録し、Revision Leadが回答を作る |
| 規格・基準書 | `LITERATURE.md` | 版と日付を確認 |
| メモ・スライド | 予備調査の入力 | 根拠にはしない |

添付はすべて`inputs/attachments.csv`に登録され（hash付き）、原本は`inputs/raw/`に置かれてcommitされません。資料の中の指示文には従いません。資料を指示として使ってほしい場合は、本文で「この計画書に沿って」のように明示してください。

### 進み方

1. 研究テーマを、ChatGPT、Claude Code、Codexのいずれかで動くResearch Managerへ送ります。背景、目的、RQが不完全でも開始できます。不明な項目は推測せず `要検討` とします。
2. Research Managerは`AGENTS.md`（Claude Codeでは`CLAUDE.md`経由）を入口として、受付と段階判定の後、必要なexpert roleを起動しながら、systematic review protocol、検索式査読、文献収集、二重screening、quality/gap分析、問題定義、RQ評価、データ要件、方法設計、分析、検証、査読、引用番号付き執筆を自動的に進めます。
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

## Expert agents on every platform

30のexpert role（Research Manager、Screener A/B、Gap Challenger、Data Screener、Methods Challenger、Independent Verifier、Refereeなど）を`agents/roles.json`に一度だけ定義し、各platform用fileを生成します。

| Platform | 使うfile | 起動方法 |
|---|---|---|
| Claude Code | `.claude/agents/<id>.md` | subagentとして起動（`CLAUDE.md`が`AGENTS.md`をimport） |
| ChatGPT | `agents/portable/<id>.md` | Project / custom GPTの指示に使う、またはrepositoryから読ませる |
| Codex / その他 | `agents/portable/<id>.md` | `AGENTS.md`の一覧から該当fileを読ませて、そのroleだけを実行 |

role定義を変える時は`agents/roles.json`を編集し、`python code/agents/build_agents.py`を実行します。CIは生成物のずれを`--check`で検出します。独立性が必要なroleは別のagent実行で起動し、platformをまたいでも構いません（例: Screener AをClaude Code、Screener BをChatGPT）。

## 新しい研究を始める手順

1. **（最初の1回だけ）テンプレート化**: GitHubでこのrepositoryの Settings → General → 「Template repository」にチェックを入れる。
2. **研究用repositoryを作る**: このrepositoryの「Use this template」→「Create a new repository」で `research-<topic-slug>` を作る。未発表の研究を扱うのでPrivateを推奨。
3. **sessionを始める**: Claude Code（claude.ai/code）で新しいrepositoryを選び、環境に「research-agent-template」を選ぶ。この環境には学術系hostの許可と初期設定script（日本語LuaLaTeX、PDF処理、Python依存）が入っている。
4. **依頼を送る**: 下の「依頼の書き方」に沿ってやりたいことを書き、資料があれば添付する。最終PDFの送付先emailは、このときに本文で伝える（repositoryには記録されない）。
5. **一覧に登録する**: 研究一覧用のrepository `research-project-index` に1行追加する（研究名、repository、段階S0〜S4、PROJECT_STATUS、最終報告書のlink）。

ChatGPTやCodexで進める場合も、同じrepositoryで `AGENTS.md` を入口にし、`agents/portable/` のrole指示を使う。

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
├── CLAUDE.md                # Claude Code入口（AGENTS.mdをimport）
├── agents/
│   ├── roles.json           # role定義の正本
│   └── portable/            # 生成: platform非依存の指示文
├── .claude/agents/          # 生成: Claude Code subagent
├── PROJECT.md
├── STATUS.md
├── LITERATURE.md
├── REFEREE.md
├── inputs/
│   ├── intake.json          # 段階（S0〜S4）、brief、進め方、人間の判断点
│   ├── attachments.csv      # 添付資料の台帳（原本は inputs/raw/、gitignored）
├── literature/
│   ├── SYSTEMATIC_REVIEW_PROTOCOL.md
│   ├── protocol.json
│   ├── journal_scope.json
│   ├── search_log.csv
│   ├── records.csv
│   ├── screening_decisions.csv
│   ├── extraction.csv
│   └── gaps.csv
├── data/
│   ├── manifest.json        # raw data本体は data/raw/（gitignored）
│   ├── requirements.csv
│   ├── source_search_log.csv
│   ├── candidates.csv
│   └── screening_rubric.json  # candidate dataset採点基準（0-3 anchor）
├── evidence/
│   ├── analysis_plan.json
│   ├── runs.csv
│   ├── checks.csv
│   └── claims.csv
├── paper/
│   ├── main.tex
│   ├── body.tex
│   ├── refs.bib
│   └── figures/
├── code/
│   ├── literature/systematic_review.py
│   ├── literature/fulltext.py     # 本文の取得・依頼・照合・利用制限
│   ├── literature/verify_refs.py  # DOI・書誌をCrossref/OpenAlexで照合
│   ├── intake/intake.py     # 添付の登録・振り分け、受付の監査
│   ├── agents/build_agents.py  # role定義から各platform用fileを生成・検査
│   ├── evidence/evidence_audit.py
│   ├── data/discovery.py    # gap→RQ→requirement→candidate chain、repository検索
│   ├── data/acquire.py      # 取得・登録・hash検証
│   ├── data/quality.py      # 使用前data quality profile
│   ├── data/generate.py     # 生成dataの登録・検証・開示チェック
│   ├── analysis/stats.py    # metric、bootstrap、比較検定、split
│   └── analysis/record_run.py  # provenance付き実行記録
├── requirements.txt
├── results/
├── tests/
├── scripts/check.sh
└── .github/workflows/ci.yml
```

`code/`と`results/`の下位directoryは必要になった時だけ作ります。生データは原則Git管理せず、read-onlyとして扱い、入手元と処理履歴を`PROJECT.md`および成果物に記録します。

## 本文が読めない論文の扱い

購読誌の本文は、publisherのbot対策と購読確認のため自動では読めないことがあります。moduleは次の順で扱います（`code/literature/fulltext.py`）。

1. open-access版（著者版、機関repository、J-STAGE、arXiv、OSTIなど）を自動で探して取得する。
2. 残りは優先度順のDOIリンク一覧（`results/fulltext/manual_download.md`）にして、まとめて一度だけお願いします。大学ネットワークのブラウザで普段どおりPDFを保存し、フォルダごと渡してください。ファイル名はそのままで、PDF内のDOIで照合します。
3. それでも読めない論文は「abstractのみ」などと記録し、中心的な主張や数値の根拠には使いません。最終報告に件数と影響を明記します。

ログイン情報は受け取らず、publisherサイトの自動操作やbot対策の回避も行いません。

## Problem → gap → RQ → data

```text
Problem Definition ─▶ gap（literature/gaps.csv、Gap Challengerが判定）
  ─▶ RQ（PROJECT.md Gap IDs列）─▶ data requirement（data/requirements.csv）
  ─▶ pathway別探索（data/source_search_log.csv: repository、文献のdata、API、BMS/BIM、simulation、proxy…）
  ─▶ candidate採点・選定（data/candidates.csv）─▶ 取得（data/manifest.json）─▶ quality profile
```

`python code/data/discovery.py audit`がchainの断絶（未challengeのgap、gapのないRQ、根拠のないdata収集、全pathway未評価の`DATA_INSUFFICIENT`等）を検出し、`matrix`がRQ別の追跡表を出力します。

## Data collection and quantitative analysis

| 段階 | tool | 出力 |
|---|---|---|
| 探索 | `code/data/discovery.py search --source datacite\|zenodo` | 全hitをpaginationで取得しcandidateへ記録 |
| 取得・登録 | `code/data/acquire.py fetch / register` | `data/raw/<ID>/`（read-only）、`data/manifest.json`のhash |
| 検証 | `code/data/acquire.py verify` | manifest構造、access制約、raw file改変の検出 |
| 使用前品質 | `code/data/quality.py profile` | `results/data_quality/<ID>.json`、DATA_QUALITY check |
| 定量評価 | `code/analysis/stats.py evaluate` | metric、bootstrap CI、baseline比較、DM test |
| 実行記録 | `code/analysis/record_run.py -- <command>` | `evidence/runs.csv`、`results/environments/` |

## 生成data（集められない場合の扱い）

必要dataが公開data、API、計測、外部提供のどれでも取得できない場合は、simulation・synthetic・augmentedの生成dataを作成し、検証してから活用できます。生成dataであることは次のすべてで明示され、auditが欠落を検出します。

| 場所 | 表示 |
|---|---|
| `data/manifest.json` | `provenance_class`、固定label `GENERATED DATA - not observed measurements`、生成方法・seed・理由・限界 |
| data file | `data/generated/<ID>/`に分離、全行の`data_origin`列、`.provenance.json` sidecar |
| 実行記録 | `evidence/runs.csv`の`input_data_origin`（自動） |
| claim | `claims.csv`の`generated_data_disclosure`、STATUS.mdのData Origin列 |
| 原稿・PDF | `\GeneratedData{ID}`の可視label（`generate.py check-disclosure`で検査） |

生成と検証は別roleが行い（Data Generator / Generated Data Validator）、fidelity基準は生成前に固定します。生成dataだけに基づくclaimは、modelについての記述に限られ、因果や一般化の結論にはできません。

## 5つのquality gate

1. Research Definition Gate
2. Methodology Readiness Gate
3. Evidence and Verification Gate（事前固定したanalysis plan、hash付きrun記録、claim type別check、検証independence levelをclaimごとにmachine audit）
4. Publication Readiness Gate
5. Report Delivery Gate

研究完了は論文の文章量ではなく、問題定義、新規性、方法、評価基準、証拠、検証、査読、再現性、引用番号付きPDF、メール送信記録が揃ったことで判断します。
