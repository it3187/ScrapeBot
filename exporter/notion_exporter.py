"""
AI判定結果をNotion データベースへ自動保存し、
高スコア案件をLINE Messaging APIで即座に通知するエクスポーターです。

意図: 案件判定→保存→通知を一気通貫で自動化し、
      良い案件が見つかった瞬間にスマホのLINEで即座に認知できるようにします。
"""

import os
import logging
from typing import Dict, Any, List, Optional

import requests

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


class NotionExporter:
    """
    案件のAI判定結果をNotionデータベースに保存し、
    高スコア案件はLINEでプッシュ通知する統合エクスポーターです。
    """

    NOTION_API_URL = "https://api.notion.com/v1/pages"
    NOTION_QUERY_URL = "https://api.notion.com/v1/databases/{db_id}/query"
    LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

    def __init__(self):
        """
        Notion APIとLINE Messaging APIの認証情報を.envから読み込みます。
        """
        self.notion_api_key = _load_env("NOTION_API_KEY")
        self.notion_db_id = _load_env("NOTION_DATABASE_ID")
        self.line_token = _load_env("LINE_CHANNEL_ACCESS_TOKEN")
        self.line_user_id = _load_env("LINE_USER_ID")

        self._notion_configured = bool(self.notion_api_key and self.notion_db_id)
        self._line_configured = bool(self.line_token and self.line_user_id)

        if not self._notion_configured:
            logger.warning("Notion APIの設定（NOTION_API_KEY / NOTION_DATABASE_ID）が不完全です。Notion保存は無効になります。")
        if not self._line_configured:
            logger.warning("LINE APIの設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）が不完全です。LINE通知は無効になります。")

    def _notion_headers(self) -> Dict[str, str]:
        """Notion API用のリクエストヘッダーを返します。"""
        return {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    def _is_already_saved(self, url: str) -> bool:
        """
        指定URLの案件が既にNotion DBに保存済みかチェックします。
        重複登録を防ぐための安全機構です。
        """
        if not self._notion_configured:
            return False

        try:
            query_url = self.NOTION_QUERY_URL.format(db_id=self.notion_db_id)
            payload = {
                "filter": {
                    "property": "URL",
                    "url": {
                        "equals": url
                    }
                }
            }
            response = requests.post(query_url, json=payload, headers=self._notion_headers(), timeout=15)
            if response.status_code == 200:
                results = response.json().get("results", [])
                return len(results) > 0
        except Exception as check_error:
            logger.debug(f"Notion重複チェックでエラーが発生しました（保存を続行します）: {check_error}")
        return False

    def save_to_notion(self, job: Dict[str, Any], evaluation: Dict[str, Any]) -> bool:
        """
        案件情報とAI判定結果をNotionデータベースに1ページとして保存します。

        Args:
            job: 案件データ（title, url, budget, description, category, extracted_at）
            evaluation: AI判定結果（score, decision, reason, action_advice, safety_flags）

        Returns:
            保存成功時True、失敗時False
        """
        if not self._notion_configured:
            logger.info("Notion設定が無効のため、保存をスキップします。")
            return False

        url = job.get("url", "")

        # 重複チェック
        if self._is_already_saved(url):
            logger.info(f"この案件は既にNotionに保存済みです（スキップ）: {job.get('title', '不明')[:40]}")
            return False

        # 安全フラグを文字列に整形
        safety_text = ""
        flags = evaluation.get("safety_flags", [])
        if flags:
            safety_text = " ⚠️ " + ", ".join(flags)

        # Notionページのプロパティを組み立てる
        payload = {
            "parent": {"database_id": self.notion_db_id},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": job.get("title", "無題の案件")[:100]}}]
                },
                "URL": {
                    "url": url
                }
            }
        }

        # ページ本文（blocks）に詳細情報を埋め込む
        # Notionのプロパティスキーマが不明なため、本文ブロックとして情報を載せる
        blocks = [
            self._make_heading_block("📊 AI判定結果"),
            self._make_paragraph_block(
                f"スコア: {evaluation.get('score', '?')}/5  |  判定: {evaluation.get('decision', '?')}"
            ),
            self._make_paragraph_block(f"理由: {evaluation.get('reason', '')}"),
            self._make_paragraph_block(f"推奨アクション: {evaluation.get('action_advice', '')}"),
        ]

        if safety_text:
            blocks.append(self._make_paragraph_block(f"⚠️ 安全フラグ: {safety_text}"))

        blocks.extend([
            self._make_divider_block(),
            self._make_heading_block("💼 案件情報"),
            self._make_paragraph_block(f"予算: {job.get('budget', '不明')}"),
            self._make_paragraph_block(f"カテゴリ: {job.get('category', '不明')}"),
            self._make_paragraph_block(f"取得日時: {job.get('extracted_at', '不明')}"),
            self._make_paragraph_block(f"概要: {job.get('description', '情報なし')[:1500]}"),
        ])

        payload["children"] = blocks

        try:
            response = requests.post(
                self.NOTION_API_URL,
                json=payload,
                headers=self._notion_headers(),
                timeout=15
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Notionに保存しました: {job.get('title', '不明')[:40]}")
                return True
            else:
                logger.error(f"Notion保存失敗: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as save_error:
            logger.error(f"Notion保存中にエラーが発生しました: {save_error}")
            return False

    def notify_line(self, job: Dict[str, Any], evaluation: Dict[str, Any]) -> bool:
        """
        高スコア案件をLINEにプッシュ通知します。

        Args:
            job: 案件データ
            evaluation: AI判定結果

        Returns:
            送信成功時True、失敗時False
        """
        if not self._line_configured:
            logger.info("LINE設定が無効のため、通知をスキップします。")
            return False

        score = evaluation.get("score", 0)
        decision = evaluation.get("decision", "?")

        # 通知メッセージの組み立て
        message = (
            f"\n【💼 案件マッチング通知】\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📋 {job.get('title', '不明')}\n"
            f"💰 予算: {job.get('budget', '不明')}\n"
            f"📊 適合スコア: {'⭐' * score} ({score}/5)\n"
            f"🏷️ 判定: {decision}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 {evaluation.get('reason', '')}\n"
            f"🎯 {evaluation.get('action_advice', '')}\n"
            f"🔗 {job.get('url', '')}\n"
        )

        # 安全フラグがあれば追記
        flags = evaluation.get("safety_flags", [])
        if flags:
            message += f"⚠️ 注意: {', '.join(flags)}\n"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.line_token}"
        }
        payload = {
            "to": self.line_user_id,
            "messages": [{"type": "text", "text": message}]
        }

        try:
            logger.info("LINE Messaging APIでプッシュ通知を送信中...")
            response = requests.post(self.LINE_PUSH_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("✅ LINE通知の送信に成功しました！")
            return True
        except requests.RequestException as line_error:
            logger.error(f"LINE通知の送信に失敗しました: {line_error}")
            return False

    def send_summary(self, total_crawled: int, total_evaluated: int, passed_count: int, errors: List[str]):
        """
        巡回結果の日報サマリーをLINEに送信します。

        Args:
            total_crawled: 巡回した案件数
            total_evaluated: AI判定した案件数
            passed_count: 合格（スコア4以上）だった案件数
            errors: 発生したエラーの一覧
        """
        if not self._line_configured:
            return

        message = (
            f"\n【🔍 ScrapeBot 案件巡回日報】\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 巡回結果サマリー\n"
            f"・新着案件数: {total_crawled} 件\n"
            f"・AI判定実行: {total_evaluated} 件\n"
            f"・合格案件数: {passed_count} 件\n"
        )

        if errors:
            message += f"\n⚠️ エラー ({len(errors)} 件):\n"
            for err in errors[:5]:
                message += f"  - {err}\n"

        if passed_count == 0:
            message += "\n今回はターゲット条件に合う案件は見つかりませんでした。次回の巡回をお待ちください。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.line_token}"
        }
        payload = {
            "to": self.line_user_id,
            "messages": [{"type": "text", "text": message}]
        }

        try:
            requests.post(self.LINE_PUSH_URL, headers=headers, json=payload, timeout=10)
            logger.info("📱 日報サマリーをLINEに送信しました。")
        except Exception as summary_error:
            logger.error(f"日報サマリーの送信に失敗しました: {summary_error}")

    # --- Notionブロック生成ヘルパー ---

    @staticmethod
    def _make_heading_block(text: str) -> Dict:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    @staticmethod
    def _make_paragraph_block(text: str) -> Dict:
        # Notionの1ブロックあたり2000文字制限を考慮して切り詰める
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
            }
        }

    @staticmethod
    def _make_divider_block() -> Dict:
        return {"object": "block", "type": "divider", "divider": {}}
