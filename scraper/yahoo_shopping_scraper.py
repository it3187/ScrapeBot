import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class YahooShoppingScraper(BaseScraper):
    """
    「Yahoo!ショッピング」の検索結果から、指定されたキーワードで商品を自動収集するためのクラスです。
    """

    def __init__(self, delay_seconds: float = 3.0):
        """
        初期設定を行います。親クラスの初期設定を引き継ぎます。
        """
        super().__init__(delay_seconds=delay_seconds)
        # Yahoo!ショッピングの汎用キーワード検索用URLです。
        self.base_search_url = "https://shopping.yahoo.co.jp/search?p={}"

    def _parse_spec_from_title(self, name: str) -> Dict[str, str]:
        """
        商品のタイトル（商品名）から、スペック情報（CPU、メモリ、ストレージ）を抜き出します。
        Yahoo!ショッピングの店舗ごとの様々なタイトル記述に対応するため、柔軟なパターンマッチングを行います。
        """
        specs = {}
        
        # 1. メモリ（例:「16GB」「16G」「8G」）の検索
        mem_match = re.search(r'\b([0-9]+)\s*(?:GB|G)\b', name, re.IGNORECASE)
        if mem_match:
            # 一般的にパソコンのメモリは4GB〜128GBの範囲に収まります
            val = int(mem_match.group(1))
            if 4 <= val <= 128:
                specs["memory"] = f"{val}GB"
                
        # 2. ストレージ（SSD容量）（例:「256GB」「512G」「1TB」）の検索
        storage_match = re.search(r'\b([0-9]+)\s*(?:GB|G|TB)\b', name, re.IGNORECASE)
        if storage_match:
            val = int(storage_match.group(1))
            unit = storage_match.group(0)[-2:].upper() if "TB" in storage_match.group(0).upper() else "GB"
            # 128GB以上、または「TB」単位の場合にストレージとみなします
            if val >= 128 or "TB" in unit:
                specs["storage"] = f"{val}{unit}"
                
        # 3. CPU（例:「M1」「M2 Pro」「Core i5」「M3 Max」など）の検索
        cpu_match = re.search(r'(Core\s*[a-zA-Z0-9\-]+|M[12345](?:\s*(?:Pro|Max))?)', name, re.IGNORECASE)
        if cpu_match:
            specs["cpu"] = cpu_match.group(1)
            
        return specs

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """
        Yahoo!ショッピングから、指定されたキーワードで商品を検索し、リスト形式で返します。
        """
        search_url = self.base_search_url.format(query)
        products = []
        
        try:
            # 1. HTMLデータをダウンロード
            html_content = self._get_page_content(search_url)
            
            # 2. BeautifulSoupで解析
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 3. Yahoo!ショッピングの商品カード要素を取得します。
            # CSSモジュールのハッシュ値（ランダム文字列）に対処するため、前方一致や部分一致で探します。
            items = soup.find_all(class_=lambda x: x and "SearchResultItem__" in x and 
                                     not any(k in x for k in ["detailLink", "price", "image", "store", "brand", "quickView", "contents", "point", "storeBadges"]))
            
            logger.info(f"「Yahoo!ショッピング」から「{query}」の検索候補 {len(items)} 件を取得しました。パースを開始します。")

            for item in items:
                try:
                    # 商品名（タイトル）と詳細URL
                    # class名に「detailLink」を含む aタグ を探します
                    link_tag = item.find("a", class_=lambda x: x and "detailLink" in x)
                    if not link_tag:
                        continue
                    title = link_tag.text.strip()
                    href = link_tag.get("href")

                    # 価格
                    # class名に「ItemPrice__」または「PriceInfo__」を含む要素を探します
                    price_tag = item.find(class_=lambda x: x and "ItemPrice__" in x)
                    if not price_tag:
                        price_tag = item.find(class_=lambda x: x and "PriceInfo__" in x)
                        
                    price_str = price_tag.text.strip() if price_tag else "0"
                    price_digits = "".join(re.findall(r'\d+', price_str))
                    price = int(price_digits) if price_digits else 0

                    # 店舗名
                    # class名に「SearchResultItemStore__」を含む要素を探します
                    store_tag = item.find(class_=lambda x: x and "SearchResultItemStore__" in x)
                    store_name = store_tag.text.strip() if store_tag else "Yahoo!ショッピング店舗"

                    # 状態（Yahoo!ショッピングは中古専門店ではないため、商品名から「中古」等を推測します）
                    status = "新品"
                    if any(k in title for k in ["中古", "展示品", "良好品", "訳あり", "良品", "美品", "Bランク", "Aランク"]):
                        status = "中古"

                    # 4. 【超拡張設計】スペック情報を拡張属性（attributes）に格納
                    attributes = {}
                    if any(k in query.lower() or k in title.lower() for k in ["macbook", "ipad", "iphone"]):
                        specs = self._parse_spec_from_title(title)
                        if specs:
                            attributes.update(specs)

                    # MacBook本体であるか判定（アクセサリー、周辺機器、他製品を除外します）
                    if not self.is_macbook_body(title):
                        continue

                    # 共通データ形式にマッピング
                    product_data = {
                        "name": title,
                        "price": price,
                        "status": status,
                        "url": href,
                        "shop_name": store_name,
                        "attributes": attributes
                    }
                    products.append(product_data)

                except Exception as item_error:
                    logger.error(f"Yahoo!ショッピングの個別商品の解析中にエラーが発生しました（スキップします）: {item_error}")
                    continue

        except Exception as e:
            logger.error(f"Yahoo!ショッピングからのデータ収集に失敗しました: {e}")
            
        return products
