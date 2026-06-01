import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class IosisScraper(BaseScraper):
    """
    「イオシス (Iosis)」の中古・新品販売ページから、指定されたキーワードで商品を自動収集するためのクラスです。
    """

    def __init__(self, delay_seconds: float = 3.0):
        """
        初期化処理を行います。親クラスの初期設定を引き継ぎます。
        """
        super().__init__(delay_seconds=delay_seconds)
        # イオシスの検索窓からのアクセス先（ベースURL）です。
        self.base_search_url = "https://iosys.co.jp/items?q={}"

    def _parse_spec_from_title(self, title: str) -> Dict[str, str]:
        """
        商品のタイトル（商品名）から、スペック情報（CPU、メモリ、SSD容量）を抜き出す補助ロジックです。
        家電製品（特にMacBook等）の場合、タイトル内に「【Apple M1/8GB/256GB SSD】」などの形式で含まれています。
        """
        specs = {}
        
        # すべての隅付き括弧【 】の中身を抽出します。
        matches = re.findall(r'【([^】]+)】', title)
        for candidate in matches:
            # スペック情報は通常「/」で区切られている特徴があります（例: Apple M1/8GB/256GB SSD）
            if '/' in candidate:
                parts = candidate.split('/')
                
                # 分割したパーツから各スペックを割り当てます
                if len(parts) >= 1:
                    specs["cpu"] = parts[0].strip()
                if len(parts) >= 2:
                    specs["memory"] = parts[1].strip()
                if len(parts) >= 3:
                    # 「SSD」という文字を除去してスッキリさせます
                    specs["storage"] = parts[2].replace("SSD", "").strip()
                break
                
        return specs

    def search_items(self, query: str) -> List[Dict[str, Any]]:
        """
        イオシスの検索ページから、指定されたキーワードで商品を検索し、リスト形式で返します。
        """
        # 特殊文字などをURLエンコードしやすくするためにフォーマットします。
        search_url = self.base_search_url.format(query)
        products = []
        
        try:
            # 1. 共通クラスのメソッドを使ってHTMLデータをダウンロード（安全なスリープを挟みます）
            html_content = self._get_page_content(search_url)
            
            # 2. BeautifulSoupでHTMLを解析
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 3. 商品リストを包んでいる入れ物（ul.items-container）を探します
            container = soup.find(class_="items-container")
            if not container:
                logger.warning(f"「イオシス」にてキーワード「{query}」に合致する商品が見つからなかったか、構造が変更されています。")
                return []

            # 4. コンテナ内の各商品要素（li.item）をすべて取得します
            items = container.find_all("li", class_="item")
            logger.info(f"「イオシス」から「{query}」の検索候補 {len(items)} 件を取得しました。パースを開始します。")

            for item in items:
                try:
                    # 商品名（タイトル）の取得
                    name_tag = item.find(class_="name")
                    if not name_tag:
                        continue
                    title = name_tag.text.strip()

                    # 価格の取得と数値型（int）への変換
                    price_tag = item.find(class_="price")
                    if not price_tag:
                        continue
                    price_str = price_tag.text.strip()
                    price_digits = "".join(re.findall(r'\d+', price_str))
                    price = int(price_digits) if price_digits else 0

                    # 状態ランクの取得（例：中古Aランク、未使用品など）
                    condition_tag = item.find(class_="condition")
                    condition = condition_tag.text.strip() if condition_tag else "不明"

                    # 詳細ページのURLを取得（相対パスを絶対URLへ変換）
                    link_tag = item.find("a")
                    href = link_tag.get("href") if link_tag else ""
                    url = f"https://iosys.co.jp{href}" if href and not href.startswith("http") else href

                    # 5. 【超拡張設計】スペック情報を拡張属性（attributes）に格納します。
                    # 「MacBook」や「iPad」などの家電製品の場合のみスペック解析を試みます。
                    attributes = {}
                    if any(k in query.lower() or k in title.lower() for k in ["macbook", "ipad", "iphone"]):
                        specs = self._parse_spec_from_title(title)
                        if specs:
                            attributes.update(specs)

                    # MacBook本体であるか判定（アクセサリー、周辺機器、他製品を除外します）
                    if not self.is_macbook_body(title):
                        continue

                    # 共通データ形式に綺麗にマッピングします
                    product_data = {
                        "name": title,
                        "price": price,
                        "status": condition,
                        "url": url,
                        "shop_name": "イオシス",
                        "attributes": attributes
                    }
                    products.append(product_data)

                except Exception as item_error:
                    logger.error(f"イオシスの個別商品の解析中にエラーが発生しました（スキップします）: {item_error}")
                    continue

        except Exception as e:
            logger.error(f"イオシスからのデータ収集に失敗しました: {e}")
            
        return products
