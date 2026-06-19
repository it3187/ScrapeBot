# Snitch: 自律型「何でも情報屋」エージェントシステム

ネット上の様々な場所から必要な情報を自律的に収集（クローリング・スクレイピング）し、独自のロジックやAI（Gemini等）を用いて「今、自分にとって本当に価値があるか」を目利き・評価し、必要なものだけをLINEやNotionなどの指定チャネルへ密告（通知・保存）する、最強のパーソナル情報配信システムです。

---

## 💡 コンセプト・開発動機
情報過多の現代において、自分に必要な「お買い得なガジェット」「すぐに稼げる副業案件」「急上昇中のトレンド」などの有益な情報は、膨大なノイズの中に埋もれています。

毎日手動で複数のサイトを何度も巡回してチェックするのは、多大な時間と労力がかかります。また、その情報が「本当に価値があるか」を瞬時に見分けるには、専門知識や過去の相場データが必要です。

**Snitch**は、この「収集 ➔ 価値判定（目利き） ➔ 通知・ストック」のプロセスを完全自動化し、あなた専属の「何でも情報屋」として24時間働き続けます。

---

## 🏗️ システムの構造（アーキテクチャ）
本システムは、機能ごとに疎結合に設計されており、新しい収集ソースや評価基準を簡単に追加・拡張できる汎用的な構造をとっています。

```mermaid
graph TD
    subgraph 1. 収集層 (Gatherers / Crawlers)
        A1[中古ECスクレイパー]
        A2[クラウドソーシング・クローラー]
        A3[トレンド・SNSクローラー]
    end

    subgraph 2. 蓄積・評価層 (Analyzers / Evaluators)
        B1[(統合データベース)]
        B2[価格相場分析エンジン]
        B3[Gemini AI 適合度判定]
    end

    subgraph 3. 通知・出力層 (Dispatchers / Exporters)
        C1[LINE プッシュ通知]
        C2[Notion データベース保存]
    end

    A1 & A2 & A3 -->|生データ収集| B1
    B1 --> B2 & B3 -->|精査・目利き| C1 & C2
```

### 1. 収集層 (Gatherers / Crawlers)
*   **ガジェット巡回 (`main.py` & `scraper/`):** イオシス、じゃんぱら、Yahoo!ショッピング等から中古デバイスの在庫・価格情報を安全に収集します。
*   **案件巡回 (`job_hunter.py` & `crawler/`):** クラウドワークス等のクラウドソーシングサイトから公開案件をPlaywright等で自動巡回します。

### 2. 蓄積・評価層 (Analyzers / Evaluators)
*   **価格統計分析 (`analyzer/`):** 同一スペックグループの過去データから市場の平均相場を自動算出し、基準を上回る割引率のお買い得商品を検知します。
*   **AI目利き判定 (`evaluator/`):** 収集した案件データをGemini API等のLLMに投入し、「バナー制作の自動化ワークフローに適合するか」などの実用性をスコア判定します。

### 3. 通知・出力層 (Dispatchers / Exporters)
*   **LINE通知 (`notifier/`):** 「超お買い得品」や「AIが合格判定した超優良案件」など、即時アクションが必要な情報をLINE Messaging API経由で直接あなたのスマホにプッシュ通知します。
*   **Notion保存 (`exporter/`):** 蓄積や将来の分析用に、優良情報をNotionデータベースに自動登録します。

---

## 📂 フォルダ構成

```text
Snitch/
├── main.py                    # 中古ガジェット相場監視のエントリポイント
├── job_hunter.py              # 副業・公開案件監視のエントリポイント
├── requirements.txt           # 依存ライブラリ一覧
├── config.json.template       # LINE等の設定テンプレート
├── .env.template              # AI APIキーやNotion等の設定テンプレート
├── snitch_spec.md             # システム詳細仕様書
│
├── scraper/                   # スクレイピングモジュール（ガジェット収集）
├── crawler/                   # Playwrightクローラーモジュール（案件・その他収集）
├── analyzer/                  # 価格相場・統計分析モジュール
├── evaluator/                 # AI判定・目利きモジュール（Gemini API等）
├── notifier/                  # LINEなどの外部通知モジュール
└── exporter/                  # Notionデータベースなどの外部保存モジュール
```

---

## 🚀 セットアップと実行手順

### 1. 依存ライブラリのインストール
Python環境で、必要なパッケージを一括導入します。
```bash
pip install -r requirements.txt
playwright install  # クローラー用のブラウザバイナリをインストール
```

### 2. 設定ファイルの準備
1. `config.json.template` をコピーして `config.json` を作成し、LINE Messaging APIの認証情報を記述します。
2. `.env.template` をコピーして `.env` を作成し、Gemini APIキーやNotion APIキー、各種巡回キーワードを設定します。

### 3. システムの実行

*   **ガジェット価格の相場監視:**
    ```bash
    python main.py
    # または run_snitch.bat の実行
    ```

*   **公開案件の自動巡回・AI判定:**
    ```bash
    python job_hunter.py
    # または run_job_hunter.bat の実行
    ```
