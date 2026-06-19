# ScrapeBot - WBS / タスク分解リスト (tasks.md)

本ドキュメントは、仕様駆動開発（SDD）に基づいて `ScrapeBot` プロジェクトのタスクを木構造（WBS）で管理します。
これらのタスクは、Notionのタスク管理データベースの「親子タスク」および「依存関係」と対応します。

---

## 📅 WBS（Work Breakdown Structure）

- [ ] `[ScrapeBot-Parent]` ScrapeBot システムの構築 (親タスク)
  - [ ] `[ScrapeBot-001]` Playwright 巡回クローラーの作成 (依存関係: なし)
  - [ ] `[ScrapeBot-002]` Gemini API 連携による案件判定エンジンの実装 (依存関係: なし)
  - [ ] `[ScrapeBot-003]` 判定結果の Notion / LINE 自動出力の実装 (依存関係: `[ScrapeBot-001]`, `[ScrapeBot-002]` に依存)
  - [ ] `[ScrapeBot-004]` 統合自動テストの実行とデプロイ (依存関係: `[ScrapeBot-003]` に依存)

---

## 🛠 タスク詳細 & 予定期間

| タスクID | タスク名 | 期間目安 | 担当 | 依存先 |
| :--- | :--- | :--- | :--- | :--- |
| `ScrapeBot-001` | クローラー作成 | 2日 | メタボ | なし |
| `ScrapeBot-002` | Gemini API判定実装 | 2日 | Agy先生 | なし |
| `ScrapeBot-003` | 出力・通知実装 | 1日 | 共同 (Pair) | 001, 002 |
| `ScrapeBot-004` | 統合テスト・デプロイ | 1日 | Agy先生 | 003 |
