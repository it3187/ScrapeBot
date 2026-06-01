import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DataManager:
    """
    データ（JSONファイル）の「金庫番（管理・保存）」を担当するクラスです。
    過去に保存されたデータを読み込み、新しく収集したデータと重複なくマージ（統合）して保存します。
    """

    def __init__(self):
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

    def load_data(self, filepath: str) -> List[Dict[str, Any]]:
        """
        ファイルから蓄積された過去のデータを読み込みます。
        その際、自動的にアクセサリーや周辺機器などの不要なデータをお掃除（クレンジング）します。
        
        Args:
            filepath (str): JSONファイルのパス
            
        Returns:
            List[Dict[str, Any]]: 読み込んだ商品データのリスト（存在しない場合は空リスト）
        """
        if not os.path.exists(filepath):
            logger.info(f"データファイル '{filepath}' が見つかりません。新規作成します。")
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 自動クレンジング：MacBook本体の情報のみを残します
                original_count = len(data)
                cleaned_data = [item for item in data if self.is_macbook_body(item.get("name", ""))]
                cleaned_count = len(cleaned_data)
                
                # もしアクセサリー類が除外された形跡があれば、データベースファイル自体も上書きしてお掃除します
                if cleaned_count < original_count:
                    logger.info(f"自動クレンジング: 蓄積データからアクセサリーや他製品を除外しました ({original_count}件 ➔ {cleaned_count}件)")
                    try:
                        with open(filepath, "w", encoding="utf-8") as f_write:
                            json.dump(cleaned_data, f_write, indent=4, ensure_ascii=False)
                        logger.info("クレンジング済みの綺麗なデータをファイルに保存し直しました。")
                    except Exception as save_err:
                        logger.error(f"クレンジングデータの保存中にエラーが発生しました: {save_err}")
                
                logger.info(f"データファイルから {cleaned_count} 件のレコードを読み込みました。")
                return cleaned_data
        except Exception as e:
            logger.error(f"データファイルの読み込み中にエラーが発生しました: {e}")
            return []

    def merge_and_save(self, new_data: List[Dict[str, Any]], filepath: str) -> List[Dict[str, Any]]:
        """
        過去のデータと新しく取得したデータをマージし、重複（同じURL）を排除してファイルに保存します。
        新着データからもアクセサリーや周辺機器、他製品を自動で除外します。
        すでに同じ商品がある場合は、最新の価格や状態の情報にアップデートします。
        
        Args:
            new_data (List[Dict[str, Any]]): 新しく収集した商品のリスト
            filepath (str): 保存先のファイルパス
            
        Returns:
            List[Dict[str, Any]]: マージ後の全商品リスト
        """
        # 1. 過去のデータを読み込む (load_data 内で自動クレンジングが実行されます)
        existing_data = self.load_data(filepath)
        
        # 2. 検索と重複チェックを高速に行うため、URLをキーにした辞書にマッピングします
        # （URLが同一商品は「同一商品」とみなします）
        merged_dict = {item["url"]: item for item in existing_data}
        
        updated_count = 0
        added_count = 0
        skipped_count = 0
        
        # 3. 新着データを1つずつ処理します
        for item in new_data:
            # MacBook本体のデータのみを対象とし、アクセサリーや他製品はマージ対象からスキップします
            if not self.is_macbook_body(item.get("name", "")):
                skipped_count += 1
                continue
                
            url = item["url"]
            if url in merged_dict:
                # すでに存在する商品は、価格や状態などを最新のものにアップデートします
                merged_dict[url] = item
                updated_count += 1
            else:
                # 新しいURLの商品は新規追加します
                merged_dict[url] = item
                added_count += 1
                
        # 4. 辞書からリストに戻します
        final_list = list(merged_dict.values())
        
        logger.info(f"データマージ結果: 新規追加 {added_count} 件, 最新情報更新 {updated_count} 件, アクセサリー等除外 {skipped_count} 件 (合計蓄積数: {len(final_list)} 件)")
        
        # 5. ファイルにUTF-8形式で綺麗にインデントを揃えて書き出します
        try:
            # 親ディレクトリが存在しない場合は作成します
            dir_name = os.path.dirname(filepath)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
                
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(final_list, f, indent=4, ensure_ascii=False)
            logger.info(f"蓄積データを '{filepath}' に正常に保存しました。")
            
        except Exception as e:
            logger.error(f"データの保存中にエラーが発生しました: {e}")
            
        return final_list
