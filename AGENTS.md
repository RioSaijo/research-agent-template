# AGENTS.md

このfileは、このrepositoryで作業するAI agentの入口である。

1. 最初に`AGENTS_CORE.md`を読む。
2. Research Managerは通常`PROJECT.md`と`STATUS.md`だけを読み、必要な正本を段階的に追加する。
3. repositoryの記録を会話履歴より優先する。
4. 入力を受けたら、`literature/SYSTEMATIC_REVIEW_PROTOCOL.md`に従いprotocol lock、検索式査読、database/seed-journal検索、重複除去、独立二重screening、quality appraisal、citation chasing、gap challengeを開始し、その結果から問題定義、RQ評価、data requirement、methodology designへ進む。
5. 不明事項は根拠なく補わず`要検討`とする。ただし不足だけを理由に研究を停止しない。
6. RQ、主要なProblem Definition、Objective、Scope、Central Contribution、PARK判断は人間の承認なしに確定変更しない。
7. テーマ受領後は、実行可能な次taskがある限りphaseごとの確認を求めず、分析、検証、査読、revision、執筆まで継続する。
8. 本文は数字式引用`[1]`を用い、すべてのreferenceを検証可能な原典へ結びつける。
9. 最終成果は検証済みPDFとして生成し、実行時に指定されたrecipientへGmailで送信する。送信成功を確認し、`STATUS.md`へPDF path、送信日時、message IDを記録するまで完了としない。
10. 最終応答は研究報告書として提出し、結論だけでなく根拠、反証試行、limitations、未解決事項、成果物link、delivery statusを含める。
11. 報告書の章立てと分量は固定せず、研究type、結果、evidence量、読者、target venueに適応させる。必要なdatabase、API、connector、公式sourceは利用可能なら検索・取得し、利用不能なsourceを検索済みと扱わない。

詳細な運用規則、role、quality gate、security、writing policyは`AGENTS_CORE.md`を正本とする。

<!-- agents:begin -->

## Expert agent roles

<!-- Generated from agents/roles.json by code/agents/build_agents.py. Do not edit; edit roles.json. -->

role定義の正本は`agents/roles.json`。同じ定義から各platform用fileを生成するため、どのplatformでも同じroleを使える。

- Claude Code: `.claude/agents/<id>.md`のsubagentとして起動する（例: 「data-screener agentでDR-01の候補を採点」）。
- ChatGPT: `agents/portable/<id>.md`をProject/custom GPTの指示として使うか、repositoryから読ませる。
- Codex / その他: `agents/portable/<id>.md`を読み、そのroleだけを実行する。
- 独立性が必要なrole（独立性欄）は、platformを問わず別のagent実行・別contextで起動する。

| Role | Gate | Independent of | Claude Code | Portable |
|---|---|---|---|---|
| Research Manager | 1, 2, 3, 4, 5 | - | `.claude/agents/research-manager.md` | `agents/portable/research-manager.md` |
| Review Protocol Lead | 1 | screener-a, screener-b | `.claude/agents/review-protocol-lead.md` | `agents/portable/review-protocol-lead.md` |
| Search Strategist | 1 | search-peer-reviewer | `.claude/agents/search-strategist.md` | `agents/portable/search-strategist.md` |
| Search Peer Reviewer | 1 | search-strategist | `.claude/agents/search-peer-reviewer.md` | `agents/portable/search-peer-reviewer.md` |
| Database / Journal Harvester | 1 | - | `.claude/agents/literature-harvester.md` | `agents/portable/literature-harvester.md` |
| Metadata Curator | 1 | - | `.claude/agents/metadata-curator.md` | `agents/portable/metadata-curator.md` |
| Screener A | 1 | screener-b, eligibility-adjudicator | `.claude/agents/screener-a.md` | `agents/portable/screener-a.md` |
| Screener B | 1 | screener-a, eligibility-adjudicator | `.claude/agents/screener-b.md` | `agents/portable/screener-b.md` |
| Eligibility Adjudicator | 1 | screener-a, screener-b | `.claude/agents/eligibility-adjudicator.md` | `agents/portable/eligibility-adjudicator.md` |
| Quality Appraiser / Evidence Extractor | 1 | - | `.claude/agents/quality-appraiser.md` | `agents/portable/quality-appraiser.md` |
| Citation Chaser | 1 | - | `.claude/agents/citation-chaser.md` | `agents/portable/citation-chaser.md` |
| Gap Analyst | 1 | gap-challenger | `.claude/agents/gap-analyst.md` | `agents/portable/gap-analyst.md` |
| Gap Challenger | 1 | gap-analyst | `.claude/agents/gap-challenger.md` | `agents/portable/gap-challenger.md` |
| Review Auditor | 1 | research-manager, screener-a, screener-b | `.claude/agents/review-auditor.md` | `agents/portable/review-auditor.md` |
| Problem / RQ Assessor | 1 | gap-analyst | `.claude/agents/problem-rq-assessor.md` | `agents/portable/problem-rq-assessor.md` |
| Data Requirement Analyst | 2 | - | `.claude/agents/data-requirement-analyst.md` | `agents/portable/data-requirement-analyst.md` |
| Data Source Scout | 2 | data-screener | `.claude/agents/data-source-scout.md` | `agents/portable/data-source-scout.md` |
| Data Screener | 2 | data-source-scout, data-verifier | `.claude/agents/data-screener.md` | `agents/portable/data-screener.md` |
| Data Verifier | 2 | data-screener | `.claude/agents/data-verifier.md` | `agents/portable/data-verifier.md` |
| Data Steward | 2, 3 | - | `.claude/agents/data-steward.md` | `agents/portable/data-steward.md` |
| Methodology Designer | 2 | - | `.claude/agents/methodology-designer.md` | `agents/portable/methodology-designer.md` |
| Analyst | 3 | methods-challenger, independent-verifier | `.claude/agents/analyst.md` | `agents/portable/analyst.md` |
| Methods Challenger | 3 | analyst | `.claude/agents/methods-challenger.md` | `agents/portable/methods-challenger.md` |
| Independent Verifier | 3 | analyst | `.claude/agents/independent-verifier.md` | `agents/portable/independent-verifier.md` |
| Evidence Auditor | 3 | analyst, methods-challenger | `.claude/agents/evidence-auditor.md` | `agents/portable/evidence-auditor.md` |
| Reproducibility Auditor | 3, 4 | analyst | `.claude/agents/reproducibility-auditor.md` | `agents/portable/reproducibility-auditor.md` |
| Referee | 4 | revision-lead, writer, analyst | `.claude/agents/referee.md` | `agents/portable/referee.md` |
| Revision Lead | 4 | referee | `.claude/agents/revision-lead.md` | `agents/portable/revision-lead.md` |
| Writer | 4 | referee | `.claude/agents/writer.md` | `agents/portable/writer.md` |
| Delivery Officer | 5 | - | `.claude/agents/delivery-officer.md` | `agents/portable/delivery-officer.md` |

<!-- agents:end -->
