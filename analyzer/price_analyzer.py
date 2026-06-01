import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class PriceAnalyzer:
    """
    データ（JSONデータ）の「数学者（相場分析）」を担当するクラスです。
    商品をスペックやキーワードに基づいてグループ分けし、それぞれのグループの平均相場を自動計算します。
    """

    def __init__(self):
        pass

    def _generate_group_key(self, item: Dict[str, Any]) -> str:
        """
        商品のスペック（attributes）またはタイトルに基づいて、商品を分類するための「グループキー（分類記号）」を自動生成します。
        
        Args:
            item (Dict[str, Any]): 商品情報の辞書
            
        Returns:
            str: 分類用のグループキー
        """
        attrs = item.get("attributes", {})
        
        # 1. 拡張スペック（cpu, memory, storage）が存在する場合は、それを組み合わせてキーを作ります。
        # 例: 「Apple M1 / 8GB / 256GB」
        if attrs and any(k in attrs for k in ["cpu", "memory", "storage"]):
            cpu = attrs.get("cpu", "不明")
            memory = attrs.get("memory", "不明")
            storage = attrs.get("storage", "不明")
            return f"{cpu} / {memory} / {storage}"
            
        # 2. スペックがない汎用商品の場合は、タイトルから大分類キーワードを抽出してグループ化します。
        # 例: 「iPad Pro 12.9」「iPad Air」「iPad mini」など
        name = item.get("name", "")
        # iPad系
        if "ipad" in name.lower():
            for kw in ["ipad pro", "ipad air", "ipad mini", "ipad"]:
                if kw in name.lower():
                    # 第〇世代などの記述があれば、それもできるだけキーに入れます
                    gen_match = re_search_gen(name)
                    return f"{kw.upper()} ({gen_match})" if gen_match else kw.upper()
        # iPhone系
        if "iphone" in name.lower():
            for kw in ["iphone 17 pro max", "iphone 17 pro", "iphone 17", "iphone 16 pro max", "iphone 16 pro", "iphone 16", "iphone 15 pro max", "iphone 15 pro", "iphone 15", "iphone 14", "iphone 13", "iphone se"]:
                if kw in name.lower():
                    return kw.upper()
            return "IPHONE一般"
            
        # 3. それ以外は、店名や余計な文字を除去した簡易的な名前グループにします
        clean_name = name.split("【")[0].strip() if "【" in name else name
        clean_name = clean_name.split("（")[0].strip() if "（" in clean_name else clean_name
        return clean_name[:30] # 長すぎる場合はカットします

    def calculate_averages(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        蓄積された全データから、グループごとの平均価格、最低価格、最高価格、およびデータ件数を計算します。
        
        Args:
            data (List[Dict[str, Any]]): 蓄積された商品のリスト
            
        Returns:
            Dict[str, Dict[str, Any]]: グループキーをキーとし、統計情報を持つ辞書
                例: {
                    "Apple M1 / 8GB / 256GB": {
                        "average_price": 95000,
                        "min_price": 75000,
                        "max_price": 110000,
                        "count": 15
                    }
                }
        """
        groups = {}
        
        # 1. 各商品をグループごとに振り分けます
        for item in data:
            price = item.get("price", 0)
            if price <= 0:
                continue  # 価格が入っていない不正データは除外します
                
            key = self._generate_group_key(item)
            
            if key not in groups:
                groups[key] = []
            groups[key].append(price)
            
        # 2. グループごとに統計値（平均・最小・最大）を算出します
        analytics = {}
        for key, prices in groups.items():
            count = len(prices)
            avg_price = int(sum(prices) / count) # 小数点以下を四捨五入（丸め）して整数にします
            min_price = min(prices)
            max_price = max(prices)
            
            analytics[key] = {
                "average_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "count": count
            }
            
        logger.info(f"相場分析完了: 合計 {len(analytics)} 個の製品スペックグループを分析しました。")
        return analytics

def re_search_gen(name: str) -> str:
    """
    タイトルから「第7世代」「第5世代」などの表記を抽出する補助関数です。
    """
    import re
    match = re.search(r'第\s*([0-9０-９]+)\s*世代', name)
    return f"第{match.group(1)}世代" if match else ""
