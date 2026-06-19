# ScrapeBot - 設計仕様書 (design.md)

本ドキュメントは、[requirements.md](file:///s:/00_Apps/ScrapeBot/specs/requirements.md) で定義された要件を実装するためのアーキテクチャおよびデータ設計を記述します。

---

## 1. 全体アーキテクチャ (System Architecture)

```mermaid
graph TD
    A[ScrapeBot Launcher] -->|起動| B[Playwright Crawler]
    B -->|HTML取得| C[Parser Engine]
    C -->|抽出データ| D[AI Evaluator (Gemini)]
    D -->|スコア・判定| E[Exporter (Notion / JSON)]
    E -->|高評価案件| F[LINE Notifier]
```

- **Crawler Layer:** Playwright（Python版）を使用し、Cookie や User-Agent を適切に制御して隠密スクレイピングを行う。
- **AI Layer:** Google Gemini API (`gemini-3.5-flash`) を呼び出し、プロンプトにユーザープロファイル（スキル・案件の希望）を埋め込んで判定させる。
- **Storage/Integration Layer:** 抽出・判定結果をローカル JSON ログおよび Notion データベースへ書き出す。

---

## 2. データ構造 (Data Schema)

### 案件データの JSON スキーマ例
```json
{
  "id": "cw_999999",
  "title": "Pythonスクレイピングツール作成",
  "url": "https://crowdworks.jp/public/jobs/999999",
  "budget": "50,000円",
  "extracted_at": "2026-06-15T13:30:00+09:00",
  "evaluation": {
    "score": 5,
    "decision": "⭕ 合格",
    "reason": "Playwrightを使用した自動化案件であり、ユーザーのスキルに100%合致するため。",
    "action_advice": "即時応募を推奨。提案書テンプレートを用いて応募メッセージを作成してください。"
  }
}
```

---

## 3. Notion 連動設計 (Notion Integration)

- [test_notion_wbs_integration.py](file:///s:/00_Apps/Pickaxe/test_notion_wbs_integration.py) で検証された Notion WBS スキーマに従い、タスク管理DBおよび案件DBにAPI経由で直接レコードをインサートします。
- 親タスクとして「ScrapeBot開発」、子タスクとして「クローラー構築」「AI判定実装」のように階層化（WBS）してタスク管理DBに自動同期させます。
