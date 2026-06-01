import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import requests

# ログの設定：プログラムの動きを画面に見やすく表示するための設定です。
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    すべてのウェブスクレイパー（データ収集機）の土台となる基本クラスです。
    このクラスを継承して、店舗ごとのスクレイパーを作ります。
    安全第一（相手のウェブサーバーに負担をかけない）の仕組みや共通の接続ロジックをここで用意します。
    """

    def __init__(self, delay_seconds: float = 3.0):
        """
        初期設定を行います。
        
        Args:
            delay_seconds (float): リクエスト間の待ち時間（スリープ秒数）。デフォルトは安全を考慮して3秒です。
        """
        self.delay = delay_seconds
        # 一般的なブラウザ（Chromeなど）からのアクセスに見せかけるための設定ヘッダーです。
        # これがないとロボットからのアクセスとしてブロックされてしまうことがあります。
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        }

    def _get_page_content(self, url: str) -> str:
        """
        指定されたURLのウェブページを取得して、HTMLの文字データを返します。
        
        Args:
            url (str): 取得したいページのURL
            
        Returns:
            str: 取得したHTML文字列
        """
        logger.info(f"アクセス中: {url}")
        
        # 安全第一ルール：アクセスする前に指定された秒数（最低3秒）必ず待ちます。
        logger.info(f"安全のために {self.delay} 秒間待機（スリープ）します...")
        time.sleep(self.delay)

        try:
            # タイムアウトを設定し、応答がない場合にずっと待ち続けないようにします。
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # ステータスコードがエラー（404や500など）の場合に例外を発生させます。
            response.raise_for_status()
            
            # 文字化けを防ぐために、レスポンスのエンコーディングを自動判別されたものに設定します。
            response.encoding = response.apparent_encoding
            
            logger.info("ページの取得に成功しました。")
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"ページの取得中にエラーが発生しました: {e}")
            # エラーが発生した場合は、上位の処理でハンドリングできるように例外を再送出します。
            raise e

    @abstractmethod
    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """
        指定された検索キーワード（query）に基づいて商品を検索・収集し、結果をリスト形式で返す共通メソッドです。
        子クラス（各店舗用のスクレイパー）で具体的なページ解析やパース処理を実装してください。
        
        Args:
            query (str): 検索キーワード（例：「MacBook」や「iPad」など）
            
        Returns:
            List[Dict[str, Any]]: 取得した商品の情報のリスト
                形式: [
                    {
                        "name": "商品名",
                        "price": 価格(数値型),
                        "status": "状態(新品/中古など)",
                        "url": "商品詳細ページのURL",
                        "shop_name": "店舗名",
                        "attributes": {
                            "商品ジャンル固有のスペック（辞書型）"
                        }
                    },
                    ...
                ]
        """
        pass

    def is_macbook_body(self, name: str) -> bool:
        """
        商品名がMacBook本体（MacBook Air / MacBook Pro / MacBook）であるか判定します。
        周辺機器、ケース、他製品、およびM3以前の古いプロセッサ搭載モデルを除外します（M4以上のみを許可）。
        
        Args:
            name (str): 商品名
            
        Returns:
            bool: MacBook本体かつM4以上と判断できる場合はTrue、そうでない場合はFalse
        """
        name_lower = name.lower()
        
        # 1. 必須条件: 「macbook」という単語が含まれていること（大文字小文字無視）
        if "macbook" not in name_lower:
            return False
            
        # 2. 除外条件: 周辺機器やアクセサリーを表すキーワード、または「用」「for」などの接続語がある場合は除外します
        exclude_keywords = [
            "用", "for", "ケース", "カバー", "スリーブ", "バッグ", "ポーチ", "ジャケット", "スキン",
            "アダプタ", "アダプター", "充電器", "チャージャー", "バッテリー",
            "キーボード", "keyboard", "マウス", "mouse", "トラックパッド", "trackpad",
            "ケーブル", "cable", "ハブ", "hub", "ドック", "dock", "ドッキング",
            "フィルム", "シート", "プロテクター", "保護", "スタンド", "台", "コネクタ", "変換", "バンパー"
        ]
        
        for kw in exclude_keywords:
            if kw in name_lower:
                return False
                
        # Intel製プロセッサ（Core m5, Core i5, Intel搭載機など）を完全に除外します
        if "core" in name_lower or "intel" in name_lower:
            return False

        # 3. プロセッサ条件: M4以上のApple Silicon（M4, M5, M6...等）が搭載されていること
        # （M1, M2, M3の古いモデルはすべて除外します）
        import re
        if not re.search(r'\bm([4-9]|\d{2,})(?:\b|pro|max|チップ|搭載|モデル)', name_lower):
            return False
                
        # すべてのテストをクリアした場合、本物のMacBook M4以上本体データとみなします
        return True
