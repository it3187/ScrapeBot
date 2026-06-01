import argparse
import json
import logging
from scraper import IosisScraper, JanparaScraper, YahooShoppingScraper
from analyzer import DataManager, PriceAnalyzer, DealDetector
from notifier import LineNotifier

# ログの設定：プログラムの動作状況をコンソールに分かりやすく表示するための設定です。
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """
    データ収集 ➔ 重複排除蓄積 ➔ 相場価格算出 ➔ お買い得検出 ➔ LINE通知送信
    の全行程を一気通貫で全自動実行するメイン処理です。
    """
    # 1. コマンドライン引数の解析を行います
    parser = argparse.ArgumentParser(
        description="中古・総合ECから製品データを収集・マージし、平均相場より安価なお買い得品を自動検知してLINEに通知します。"
    )
    # 位置引数：検索するキーワード（デフォルトは MacBook）
    parser.add_argument(
        "query",
        nargs="?",
        default="MacBook",
        help="検索したい製品名やキーワード（デフォルト: 'MacBook'）"
    )
    # オプション引数：お買い得基準となる割引率（デフォルトは 20.0%）
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="平均相場より何%%安ければお買い得と判定するか（デフォルト: 20）"
    )
    # オプション引数：分析のみを実行するフラグ（再スクレイピングで負荷をかけない親切機能です）
    parser.add_argument(
        "--only-analysis",
        action="store_true",
        help="新規スクレイピングを実行せず、既存の蓄積データを用いて相場分析とお買い得検出のみを行います"
    )
    
    args = parser.parse_args()
    query = args.query
    threshold = args.threshold
    only_analysis = args.only_analysis
    
    # 蓄積・分析用のファイルパス
    data_filepath = "macbook_data.json"
    
    # 各モジュール（金庫番、数学者、目利き、郵便屋さん）を用意します
    data_manager = DataManager()
    price_analyzer = PriceAnalyzer()
    deal_detector = DealDetector(threshold_pct=threshold)
    line_notifier = LineNotifier(config_path="config.json")
    
    new_products = []
    
    if not only_analysis:
        # ==========================================
        # ステップ 1: 新着データ収集（スクレイピング）
        # ==========================================
        logger.info(f"=== [ステップ 1] キーワード「{query}」で新着スクレイピングを開始します ===")
        scrapers = [
            IosisScraper(delay_seconds=3.0),
            JanparaScraper(delay_seconds=3.0),
            YahooShoppingScraper(delay_seconds=3.0)
        ]
        
        for scraper in scrapers:
            shop_name = scraper.__class__.__name__.replace("Scraper", "")
            logger.info(f"【{shop_name}】からデータ収集中...")
            try:
                products = scraper.search_items(query)
                logger.info(f"【{shop_name}】から {len(products)} 件の商品データを取得しました。")
                new_products.extend(products)
            except Exception as e:
                logger.error(f"【{shop_name}】からのデータ収集中にエラーが発生しました（スキップ）: {e}")
                continue
                
        if not new_products:
            logger.warning("今回の実行で新着商品が1件も取得できませんでした。既存のデータをもとに分析を試みます。")
            
        # ==========================================
        # ステップ 2: データの蓄積（重複排除マージ保存）
        # ==========================================
        logger.info("=== [ステップ 2] データの重複チェックおよび蓄積マージを実行します ===")
        consolidated_data = data_manager.merge_and_save(new_products, data_filepath)
        
    else:
        logger.info("=== [ステップ 1&2 スキップ] 既存の蓄積データを用いて相場分析を開始します ===")
        consolidated_data = data_manager.load_data(data_filepath)
        new_products = consolidated_data

    if not consolidated_data:
        logger.error("分析対象となるデータがありません。プログラムを終了します。")
        return

    # ==========================================
    # ステップ 3: スペック別の平均相場の自動計算
    # ==========================================
    logger.info("=== [ステップ 3] スペックごとの平均相場を自動計算します ===")
    group_analytics = price_analyzer.calculate_averages(consolidated_data)
    
    # 算出したグループ別の相場を画面に一覧表示します（見やすく整理）
    logger.info("------------- スペック別 平均相場一覧 -------------")
    for key, stats in sorted(group_analytics.items(), key=lambda x: x[1]["count"], reverse=True)[:15]:
        logger.info(
            f"● {key:<35} | 平均価格: {stats['average_price']:8,}円 | "
            f"値幅: {stats['min_price']:,}〜{stats['max_price']:,}円 | "
            f"データ数: {stats['count']:2}件"
        )
    if len(group_analytics) > 15:
        logger.info(f"...他 {len(group_analytics) - 15} 個のグループを分析済み")
    logger.info("--------------------------------------------------")

    # ==========================================
    # ステップ 4: 相場より割安な「お買い得商品」の自動判定
    # ==========================================
    logger.info("=== [ステップ 4] 相場より割安な『お買い得商品』を自動検知します ===")
    bargains = deal_detector.detect_bargains(new_products, group_analytics)
    
    # 結果のコンソール出力
    logger.info("==================================================")
    if bargains:
        logger.info(f"🎉 超お買い得な商品が {len(bargains)} 件見つかりました！ (しきい値: 相場より {threshold}% 以上安い)")
        logger.info("==================================================")
        for i, item in enumerate(bargains):
            logger.info(
                f"🔥 お買い得 #{i+1} 【{item['discount_pct']}% OFF!!】\n"
                f"   商品名  : {item['name']}\n"
                f"   販売価格: {item['price']:,}円 (相場平均: {item['average_price']:,}円 | 差額: -{item['average_price'] - item['price']:,}円)\n"
                f"   状態ランク: {item['status']} | 店舗: {item['shop_name']}\n"
                f"   商品URL : {item['url']}\n"
            )
            
        # ==========================================
        # ステップ 5: LINE Notify へのプッシュ通知自動送信
        # ==========================================
        if line_notifier.channel_access_token and line_notifier.user_id:
            logger.info("=== [ステップ 5] お買い得商品のLINEプッシュ通知を自動送信します ===")
            for i, item in enumerate(bargains):
                # 差額の算出
                difference = item["average_price"] - item["price"]
                
                # LINE用に見やすいメッセージを組み立てます
                message = (
                    f"\n【🔥 お買い得品検出！ ({item['discount_pct']}% OFF)】\n"
                    f"🌟 商品名: {item['name']}\n"
                    f"💰 価格  : {item['price']:,}円\n"
                    f"📊 相場  : {item['average_price']:,}円 (差額: -{difference:,}円)\n"
                    f"✨ 状態  : {item['status']} | 店舗: {item['shop_name']}\n"
                    f"🔗 URL   : {item['url']}\n"
                )
                
                # LINEへ通知を送信します
                line_notifier.send_notification(message)
        else:
            logger.info("※LINE設定（チャネルアクセストークン/ユーザーID）が設定されていないため、LINEプッシュ通知はスキップされました。")
            logger.info("  通知を受け取りたい場合は、'config.json' に正しい接続情報を設定してください。")
            
    else:
        logger.info(f"🔎 今回はお買い得基準（相場平均より {threshold}% 以上安い）を満たす商品は検出されませんでした。")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
