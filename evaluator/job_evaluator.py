"""
クラウドワークス等から取得した案件情報を Google Gemini API に投げて、
ユーザーのスキル・希望条件との適合度をスコアリング（1〜5段階）するAI判定エンジンです。

意図: 手動で案件を1つずつ読んで判断する手間を省き、
      AIにレッドフラグ（危険信号）の検知と適合度の自動判定を任せます。
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# .envファイルのパス
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def _load_env(key: str) -> Optional[str]:
    """ScrapeBot直下の.envファイルから指定キーの値を読み込みます。"""
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip()
        except Exception:
            pass
    return None


# ユーザーのスキルと希望条件をプロンプトに埋め込むためのテンプレート
EVALUATION_PROMPT_TEMPLATE = """あなたは、フリーランスエンジニアの副業案件マッチングアドバイザーです。
以下のユーザープロファイルと案件情報を照合し、適合度を判定してください。

## ユーザープロファイル
- **保有スキル:** {user_skills}
- **希望条件:** {user_preferences}

## 判定対象の案件情報
- **案件名:** {title}
- **予算・報酬:** {budget}
- **概要:** {description}
- **カテゴリ:** {category}

## 判定基準
1. ユーザーのスキルで対応可能か（技術面）
2. 成果物納品型の案件か（短期集中で完了できるか）
3. 報酬額は妥当か（安すぎないか）
4. 以下のレッドフラグ（危険信号）がないか：
   - 不要なLINE/チャットワーク/Discord誘導
   - 「初心者歓迎！スマホで簡単！」等の詐欺疑い表現
   - テストライティング・テスト開発によるタダ働き
   - 個人情報の提示要求
   - 報酬が極端に低い（数百円レベル）
5. React/CSS（Remotion）を活用したバナー制作・バナー画像作成・ヘッダー作成等のデザイン系案件も適合（合格）判定の対象とすること

## 出力フォーマット（必ず以下のJSON形式で返してください。他のテキストは一切不要です）
```json
{{
  "score": 1〜5の整数（5が最高適合）,
  "decision": "⭕ 合格" または "△ 保留" または "✖ 不合格",
  "reason": "判定理由を1〜2文で簡潔に",
  "action_advice": "次に取るべきアクション（即応募推奨、条件要確認、スキップ等）を1文で",
  "safety_flags": ["検知された安全上の懸念事項をリストで。なければ空配列"]
}}
```
"""


class JobEvaluator:
    """
    Google Gemini API を用いて、クラウドワークスの案件情報をユーザーの
    スキル・希望条件と照合し、適合度をスコアリングする判定エンジンです。
    """

    def __init__(self):
        """
        Gemini APIクライアントの初期設定を行います。
        APIキーは ScrapeBot/.env の GEMINI_API_KEY から読み込みます。
        """
        self.api_key = _load_env("GEMINI_API_KEY")
        self.model_name = _load_env("GEMINI_MODEL") or "gemini-2.0-flash"
        self.user_skills = _load_env("USER_SKILLS") or "Python, スクレイピング"
        self.user_preferences = _load_env("USER_PREFERENCES") or "成果物納品型の案件を優先"

        if not self.api_key:
            logger.error("GEMINI_API_KEY が .env に設定されていません。AI判定機能は無効になります。")

        self._client = None

    def _get_client(self):
        """Gemini APIクライアントを遅延初期化して返します。"""
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini APIクライアントを初期化しました（モデル: {self.model_name}）")
            except Exception as init_error:
                logger.error(f"Gemini APIクライアントの初期化に失敗しました: {init_error}")
        return self._client

    def evaluate(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        1件の案件データを Gemini API に投げて適合度を判定します。

        Args:
            job: 案件データ（title, url, budget, description, category を持つ辞書）

        Returns:
            判定結果の辞書（score, decision, reason, action_advice, safety_flags）
            APIエラー時は None を返します。
        """
        client = self._get_client()
        if not client:
            logger.warning("Gemini APIクライアントが利用できないため、判定をスキップします。")
            return None

        # プロンプトを組み立てる
        prompt = EVALUATION_PROMPT_TEMPLATE.format(
            user_skills=self.user_skills,
            user_preferences=self.user_preferences,
            title=job.get("title", "不明"),
            budget=job.get("budget", "不明"),
            description=job.get("description", "情報なし"),
            category=job.get("category", "不明")
        )

        max_retries = 3
        retry_delay = 30.0

        for attempt in range(max_retries + 1):
            try:
                # レート制限対策: 15RPM制限のため、API呼び出し前に4.0秒以上待機
                time.sleep(4.0)

                logger.info(f"Gemini APIで判定中: 「{job.get('title', '不明')[:50]}...」 (試行 {attempt + 1}/{max_retries + 1})")
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )

                # レスポンスからJSONを抽出
                result_text = response.text.strip()
                evaluation = self._parse_response(result_text)

                if evaluation:
                    logger.info(
                        f"判定結果: スコア={evaluation['score']}/5 "
                        f"判定={evaluation['decision']} "
                        f"理由={evaluation['reason'][:50]}..."
                    )
                return evaluation

            except Exception as api_error:
                error_str = str(api_error)
                logger.error(f"Gemini API呼び出しエラー: {error_str}")

                # 429 (Resource Exhausted) の場合はバックオフしてリトライ
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries:
                        sleep_time = retry_delay * (2 ** attempt)
                        logger.info(f"レート制限を検知しました。{sleep_time:.1f} 秒待機してリトライします...")
                        time.sleep(sleep_time)
                        continue
                return None

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Gemini APIのレスポンステキストから構造化されたJSON判定結果を抽出します。

        意図: LLMはJSON以外のテキスト（前置きや解説文）を返すことがあるため、
             コードブロック内のJSONだけを抜き出すロバストなパーサーが必要です。
        """
        # 1. ```json ... ``` ブロックから抽出を試みる
        if "```json" in response_text:
            json_start = response_text.index("```json") + 7
            json_end = response_text.index("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.index("```") + 3
            json_end = response_text.index("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "{" in response_text:
            # 2. 最初の { から最後の } までを切り出す
            json_start = response_text.index("{")
            json_end = response_text.rindex("}") + 1
            json_str = response_text[json_start:json_end]
        else:
            logger.error(f"Gemini APIレスポンスからJSONを抽出できませんでした: {response_text[:200]}")
            return None

        try:
            result = json.loads(json_str)
            # 必須フィールドの検証
            required_keys = ["score", "decision", "reason", "action_advice"]
            for key in required_keys:
                if key not in result:
                    logger.error(f"判定結果に必須キー '{key}' が含まれていません")
                    return None
            # scoreの型変換と範囲チェック
            result["score"] = max(1, min(5, int(result["score"])))
            # safety_flagsが未定義なら空リスト
            if "safety_flags" not in result:
                result["safety_flags"] = []
            return result
        except (json.JSONDecodeError, ValueError) as parse_error:
            logger.error(f"JSON パースに失敗しました: {parse_error}\nレスポンス: {json_str[:300]}")
            return None
