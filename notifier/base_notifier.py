from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseNotifier(ABC):
    """
    すべての通知送信機（郵便屋さん）の土台となる基本クラスです。
    LINEやDiscord、Slackなど、どんなツールへ通知を送る際も共通して従うべき「設計図」を定義します。
    """

    def __init__(self):
        pass

    @abstractmethod
    def send_notification(self, message: str) -> bool:
        """
        メッセージを外部ツールに送信する抽象メソッドです。
        子クラス（各ツール用の通知送信機）で具体的な送信方法（APIリクエストなど）を実装してください。
        
        Args:
            message (str): 送信したい通知本文の文字列
            
        Returns:
            bool: 送信に成功した場合は True, 失敗した場合は False
        """
        pass
