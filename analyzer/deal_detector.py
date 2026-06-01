import logging
from typing import List, Dict, Any
from .price_analyzer import PriceAnalyzer

logger = logging.getLogger(__name__)

class DealDetector:
    """
    データ（JSONデータ）の「目利き（お買い得判定）」を担当するクラスです。
    新着商品の価格を、算出された平均相場（平均価格）と比較し、一定割合（しきい値）以上安いお買い得品を検出します。
    """

    def __init__(self, threshold_pct: float = 20.0):
        """
        初期設定を行います。
        
        Args:
            threshold_pct (float): お買い得と判定するための割引率（相場より〇〇%以上安いか）。デフォルトは20%です。
        """
        self.threshold = threshold_pct
        self.analyzer = PriceAnalyzer()

    def detect_bargains(
        self, 
        new_items: List[Dict[str, Any]], 
        group_analytics: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        新着商品リストをスキャンし、各グループの平均相場より安く、お買い得基準を満たしている商品を検出します。
        
        Args:
            new_items (List[Dict[str, Any]]): 新しく収集した（あるいは今回のマージ処理の）商品リスト
            group_analytics (Dict[str, Dict[str, Any]]): PriceAnalyzerで計算した相場情報
            
        Returns:
            List[Dict[str, Any]]: お買い得品と判定された商品のリスト（お買い得度情報付き）
        """
        bargains = []
        
        for item in new_items:
            price = item.get("price", 0)
            if price <= 0:
                continue
                
            # 1. この商品がどのスペックグループに属するかを割り出します
            key = self.analyzer._generate_group_key(item)
            
            # 2. そのグループの相場（統計情報）を取得します
            stats = group_analytics.get(key)
            if not stats:
                continue
                
            avg_price = stats["average_price"]
            count = stats["count"]
            
            # 3. 信頼性の確認：相場データが極端に少ない（例: 1件のみ）場合は、
            # 比較対象の平均価格がその商品自身の価格になってしまうため、お買い得判定からは除外（またはスキップ）します。
            # 今回は、グループ内に少なくとも2件以上のデータがある場合のみ判定を有効にします（安全設計）。
            if count < 2:
                continue
                
            # 4. 相場からの割引率（お買い得度）を計算します
            # 例: 平均 100,000円 の商品が 80,000円 なら、割引率は 20%
            discount_amount = avg_price - price
            if discount_amount <= 0:
                continue  # 相場以上の価格の場合はスキップ
                
            discount_pct = (discount_amount / avg_price) * 100.0
            
            # 5. 設定されたしきい値（例: 20%以上安い）を満たしているかを判定します
            if discount_pct >= self.threshold:
                # お買い得商品としてリストに追加します（平均価格や割引率情報も一緒に保存）
                bargain_data = item.copy()
                bargain_data["average_price"] = avg_price
                bargain_data["discount_pct"] = round(discount_pct, 1) # 小数点第一位で丸めます
                bargain_data["group_key"] = key
                bargains.append(bargain_data)
                
        # 割引率が高い順（お買い得度が高い順）に並び替えます
        bargains = sorted(bargains, key=lambda x: x["discount_pct"], reverse=True)
        
        logger.info(f"お買い得判定完了: 新着データから {len(bargains)} 件のお買い得商品を検出しました！ (割引率基準: {self.threshold}%)")
        return bargains
