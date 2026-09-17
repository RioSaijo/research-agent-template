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
