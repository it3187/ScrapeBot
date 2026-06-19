# ScrapeBot - 機能要件定義書 (requirements.md)

本ドキュメントは、仕様駆動開発（SDD）における `ScrapeBot` の機能要件を定義します。
要件定義には、曖昧さを排除するため **EARS notation (Easy Approach to Requirements Syntax)** を使用します。

---

## 1. コアシステム要件 (Core System Requirements)

### [REQ-001] 対象サイトへの接続
- **構文 (Ubiquitous):**
  - SYSTEM SHALL connect to target URLs securely using Playwright.
- **意図:** スクレイピングのブラウザオートメーション基盤として Playwright を採用し、ヘッドレス/有頭モードを切り替えて安定して接続できること。

### [REQ-002] データ抽出
- **構文 (Event-driven):**
  - WHEN the target page is fully loaded, SYSTEM SHALL extract job postings metadata (title, budget, details, url).
- **意図:** ページの読み込み完了イベントをフックし、必要な要素（DOM）を正確に抽出すること。

### [REQ-003] エラーハンドリングとリトライ
- **構文 (State-driven):**
  - WHILE target site encounters HTTP 5xx errors or timeouts, SYSTEM SHALL retry the request up to 3 times with exponential backoff.
- **意図:** 一時的なネットワーク障害やサーバー高負荷時に、即座に異常終了せず、リトライして堅牢性を高めること。

---

## 2. マッチング・フィルター要件 (Matching & Filtering)

### [REQ-004] AIマッチングスコアリング
- **構文 (Optional):**
  - WHERE AI scoring is enabled, SYSTEM SHALL analyze extracted descriptions against user skill profile and return a match score (1-5).
- **意図:** クラウドワークス等の案件情報に対し、Gemini APIを使ってユーザーのスキル（GEMINI.mdや環境変数で定義）と適合するかスコアリングすること。

---

## 3. 通知・出力要件 (Notification & Export)

### [REQ-005] LINE / Slack 通知
- **構文 (Event-driven):**
  - WHEN a high-score job match (score >= 4) is found, SYSTEM SHALL send an alert containing title and advice via LINE Messaging API.
- **意図:** 条件に合致する「優良案件」が見つかった時、リアルタイムにモバイル端末等に通知して認知漏れを防ぐこと。
