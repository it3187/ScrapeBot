import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class JanparaScraper(BaseScraper):
    """
    「じゃんぱら (Janpara)」の中古・新品販売ページから、指定されたキーワードで商品を自動収集するためのクラスです。
    """

    def __init__(self, delay_seconds: float = 3.0):
        """
        初期設定を行います。じゃんぱら用の高度なブラウザ擬態ヘッダーを定義します。
        """
        super().__init__(delay_seconds=delay_seconds)
        # じゃんぱらの実際の検索結果表示用ベースURLです。
        self.base_search_url = "https://www.janpara.co.jp/sale/search/result/?KEYWORDS={}"

        # 自動アクセスブロックを回避するための擬態ヘッダーです。
        self.headers = {
            'authority': 'www.janpara.co.jp',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ja,en-US;q=0.9,en;q=0.8',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-restore': 'navigate',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }

    def _get_page_content_janpara(self, url: str) -> str:
        """
        じゃんぱら専用のダウンロードメソッドです。文字コードの文字化け（UTF-8）を解消します。
        """
        logger.info(f"アクセス中: {url}")
        
        # 安全第一ルール：アクセスする前に指定された秒数必ず待ちます。
        logger.info(f"安全のために {self.delay} 秒間待機（スリープ）します...")
        import time
        time.sleep(self.delay)

        try:
            # 擬態ヘッダーを乗せて接続します。
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 文字化け防止のため明示的にUTF-8を指定します。
            response.encoding = 'utf-8'
            
            logger.info("ページの取得に成功しました。")
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"じゃんぱらのページ取得中にエラーが発生しました: {e}")
            raise e

    def _parse_spec_from_title(self, name: str) -> Dict[str, str]:
        """
        じゃんぱらの商品名からスペック情報（CPU、メモリ、SSD）を抜き出します。
        「/」で区切られたパーツから賢く抽出します。
        """
        specs = {}
        
        if '/' in name:
            parts = name.split('/')
            
            # メモリの取得（通常は2番目のパーツ）
            if len(parts) >= 2:
                mem_part = parts[1].strip()
                if 'G' in mem_part:
                    specs["memory"] = mem_part
                    
            # ストレージ（SSD容量）の取得（通常は3番目のパーツ）
            if len(parts) >= 3:
                st_part = parts[2].strip()
                specs["storage"] = st_part.replace("(SSD)", "").split()[0] if st_part else "不明"

            # CPUの取得（1番目のパーツの末尾周辺）
            if len(parts) >= 1:
                cpu_part = parts[0].strip()
                cpu_match = re.search(r'(Core\s+[a-zA-Z0-9]+(?:\s+\([^\)]+\))?|M[12345](?:\s+Pro|\s+Max)?|A\d+\s+Pro)', cpu_part)
                if cpu_match:
                    specs["cpu"] = cpu_match.group(1)
                else:
                    specs["cpu"] = cpu_part.split()[-1] if cpu_part.split() else "不明"
                    
        return specs

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """
        じゃんぱらから、指定されたキーワードで商品を検索し、リスト形式で返します。
        """
        search_url = self.base_search_url.format(query)
        products = []
        
        try:
            # 1. HTMLデータをダウンロード
            html_content = self._get_page_content_janpara(search_url)
            
            # 2. BeautifulSoupで解析
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 3. 商品要素（class="search_item_s"）を取得
            items = soup.find_all(class_="search_item_s")
            logger.info(f"「じゃんぱら」から「{query}」の検索候補 {len(items)} 件を取得しました。パースを開始します。")

            for item in items:
                try:
                    # 商品名（タイトル）
                    name_tag = item.find(class_="search_itemname")
                    if not name_tag:
                        continue
                    name = name_tag.text.strip().replace("\n", " ")

                    # 価格
                    price_tag = item.find(class_="search_itemprice")
                    if not price_tag:
                        continue
                    price_digits = "".join(re.findall(r'\d+', price_tag.text.strip()))
                    price = int(price_digits) if price_digits else 0

                    # 状態ランク
                    condition_tag = item.find(class_="search_itemcondition")
                    condition = condition_tag.text.strip() if condition_tag else "中古"

                    # 詳細URL
                    link_tag = item.find("a", class_="search_itemlink")
                    if not link_tag:
                        link_tag = item.find("a")
                    href = link_tag.get("href") if link_tag else ""
                    url = f"https://www.janpara.co.jp{href}" if href and not href.startswith("http") else href

                    # 4. 【超拡張設計】スペック情報を拡張属性（attributes）に格納
                    attributes = {}
                    if any(k in query.lower() or k in name.lower() for k in ["macbook", "ipad", "iphone"]):
                        specs = self._parse_spec_from_title(name)
                        if specs:
                            attributes.update(specs)

                    # MacBook本体であるか判定（アクセサリー、周辺機器、他製品を除外します）
                    if not self.is_macbook_body(name):
                        continue

                    # 共通データ形式に綺麗にマッピングします
                    product_data = {
                        "name": name,
                        "price": price,
                        "status": condition,
                        "url": url,
                        "shop_name": "じゃんぱら",
                        "attributes": attributes
                    }
                    products.append(product_data)

                except Exception as item_error:
                    logger.error(f"じゃんぱらの個別商品の解析中にエラーが発生しました（スキップします）: {item_error}")
                    continue

        except Exception as e:
            logger.error(f"じゃんぱらからのデータ収集に失敗しました: {e}")
            
        return products
