# research-agent-template

既に定義された研究テーマを、計画、文献調査、実装、検証、査読、執筆まで一貫して管理するための再利用可能な研究環境です。建築設備・建築環境、BMS/BEMS/BAS、IoT、BIM/IFC、データ工学、統計・機械学習、デジタルツイン、施設管理などを含む横断研究を想定しますが、単一分野や特定技術に固定しません。

## 運用原則

- Git repositoryを唯一の正本とし、会話履歴に研究状態を依存させません。
- ChatGPTが研究判断と管理を担当し、Codexはrepository-wideな実装等が必要な場合だけ使います。
- Research Question (RQ) をData、Method、Evaluation、Evidence、Claimへ追跡します。
- 評価基準を分析前に定義し、証拠の存在と主張の支持を区別します。
- Refereeは確認より先に反証可能性、代替説明、データ品質問題を探します。
- RQ、中心的問題、主要scope、中心的貢献の変更には人間の承認が必要です。

## 開始方法

1. `PROJECT.md` のResearch Background、Motivation、Problem Definition、Research Objective、Research Questionsを記入します。不明な項目は推測せず `要検討` とします。
2. ChatGPTにrepositoryを渡します。`AGENTS.md`を入口として自動的に文献調査、問題定義、RQ評価、データ要件、方法設計を開始します。
3. `STATUS.md`で現在のphase、quality gate、task、Claim Evidence Tableを確認します。
4. 重要な研究方針変更や人間だけが取得できる資源が必要になった場合に限り、人間が判断します。

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
├── paper/
│   ├── main.tex
│   ├── refs.bib
│   └── figures/
├── code/
├── results/
├── tests/
├── scripts/check.sh
└── .github/workflows/ci.yml
```

`code/`と`results/`の下位directoryは必要になった時だけ作ります。生データは原則Git管理せず、read-onlyとして扱い、入手元と処理履歴を`PROJECT.md`および成果物に記録します。

## 4つのquality gate

1. Research Definition Gate
2. Methodology Readiness Gate
3. Evidence and Verification Gate
4. Publication Readiness Gate

研究完了は論文の文章量ではなく、問題定義、新規性、方法、評価基準、証拠、検証、査読、再現性が揃ったことで判断します。

