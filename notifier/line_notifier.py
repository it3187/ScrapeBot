import os
import json
import logging
import requests
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)

class LineNotifier(BaseNotifier):
    """
    最新の「LINE Messaging API」を使用して、登録されたユーザーのLINEアプリ宛てに
    プッシュメッセージを直接送信するクラスです。（LINE Notify終了に伴う代替機能）
    """

    def __init__(self, config_path: str = "config.json"):
        """
        初期設定を行います。設定ファイル（config.json）からチャネルアクセストークンとユーザーIDを読み込みます。
        
        Args:
            config_path (str): 設定ファイルのパス（デフォルト: 'config.json'）
        """
        super().__init__()
        self.channel_access_token = ""
        self.user_id = ""
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        """
        設定ファイルからアクセストークンとユーザーIDをロードします。
        """
        if not os.path.exists(self.config_path):
            logger.warning(
                f"設定ファイル '{self.config_path}' が見見つかりません。\n"
                f"テンプレートをコピーして '{self.config_path}' を作成し、設定を行ってください。"
            )
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                token = config.get("line_channel_access_token", "").strip()
                user_id = config.get("line_user_id", "").strip()
                
                # デフォルトの日本語プレースホルダーのままになっているかチェックします
                if not token or "ここにあなたの" in token or "入力してください" in token or \
                   not user_id or "ユーザーIDを入力" in user_id:
                    logger.warning(
                        f"設定ファイル '{self.config_path}' 内の情報がデフォルトのまま、あるいは未設定です。\n"
                        f"LINE Developersにて『チャネルアクセストークン』と『ユーザーID』を取得し、\n"
                        f"'{self.config_path}' に設定するまでLINEプッシュ通知機能は無効になります。"
                    )
                else:
                    self.channel_access_token = token
                    self.user_id = user_id
                    logger.info("LINE Messaging API の設定を正常に読み込みました！")
                    
        except Exception as e:
            logger.error(f"設定ファイルの解析中にエラーが発生しました: {e}")

    def send_notification(self, message: str) -> bool:
        """
        LINE Messaging API（プッシュメッセージエンドポイント）を使用してメッセージを送信します。
        
        Args:
            message (str): 送信するメッセージ内容
            
        Returns:
            bool: 送信に成功した場合は True, 失敗した場合は False
        """
        # 設定が揃っていない場合は送信をスキップします
        if not self.channel_access_token or not self.user_id:
            logger.warning("LINEチャネルアクセストークンまたはユーザーIDが未設定のため、通知の送信をスキップします。")
            return False

        # LINE Messaging API のプッシュメッセージ送信先エンドポイントです
        url = "https://api.line.me/v2/bot/message/push"
        
        # API仕様に基づいたヘッダー（JSON送信およびベアラートークン認証）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        
        # 送信データ構造（誰に送るか 'to'、メッセージリスト 'messages'）
        payload = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }

        try:
            logger.info("LINE Messaging API を通じてプッシュ通知を送信中...")
            # HTTP POSTリクエストをJSON形式で送信します
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            # ステータスコードチェック
            response.raise_for_status()
            
            logger.info("LINEへのプッシュメッセージ送信に成功しました！")
            return True
            
        except requests.RequestException as e:
            logger.error(f"LINEへのメッセージ送信中にエラーが発生しました: {e}")
            if response is not None:
                logger.error(f"LINE API レスポンス詳細: {response.text}")
            return False
