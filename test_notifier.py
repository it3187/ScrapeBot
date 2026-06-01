import logging
from notifier import LineNotifier

# ログの設定：プログラムの動作状況を表示します
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_notification():
    """
    最新の LINE Messaging API へのテストプッシュメッセージが正しく届くかを検証するスクリプトです。
    """
    logger.info("=== LINE Messaging API テスト通知処理を開始します ===")

    # 1. LINE通知送信機を起動します（自動的に config.json をロードします）
    notifier = LineNotifier(config_path="config.json")

    # 設定が揃っていない場合は、2026年最新のMessaging API導入手順を非常に丁寧に表示します
    if not notifier.channel_access_token or not notifier.user_id:
        logger.error("【エラー】LINEアクセストークンまたはユーザーIDが設定されていません！")
        logger.info("\n--------------------------------------------------")
        logger.info("🔔 LINE Messaging API（公式メッセージ機能）簡単設定手順 🔔")
        logger.info("LINE Notifyのサービス終了に伴い、公式のメッセージ機能を使用して通知を送ります（無料です）。")
        logger.info("1. LINE Developers コンソールにログインします: https://developers.line.biz/")
        logger.info("2. 『新規プロバイダー』を作成し、その中に『Messaging APIチャネル』を新規作成します。")
        logger.info("3. チャネルの設定が完了したら、表示される『QRコード』をご自身のスマホのLINEアプリで読み取り、友だち追加します（これで通知を受け取る窓口ができます）。")
        logger.info("4. 【ユーザーIDの取得】: チャネル設定の『チャネル基本設定』タブの一番下にある『あなたのユーザーID（Uxxxx...）』をコピーして、'config.json' の 'line_user_id' に貼り付けます。")
        logger.info("5. 【アクセストークンの取得】: 『Messaging API』タブの一番下にある『チャネルアクセストークン（長期）』の『発行』ボタンを押し、生成された長い英数字のキーをコピーして、'config.json' の 'line_channel_access_token' に貼り付けます。")
        logger.info("6. config.json を上書き保存して、再度このスクリプトを実行してください！")
        logger.info("--------------------------------------------------\n")
        return

    # 2. テスト用のダミーお買い得データを用意します
    dummy_item = {
        "name": "【ダミーテストお買い得品】MacBook Air 13インチ 【Apple M1/8GB/256GB SSD】",
        "price": 58000,
        "average_price": 83500,
        "discount_pct": 30.5,
        "status": "中古Aランク",
        "shop_name": "イオシス",
        "url": "https://iosys.co.jp/items/pc/macbook"
    }

    # 3. LINE送信用にメッセージを美しくデコレーションして組み立てます
    difference = dummy_item["average_price"] - dummy_item["price"]
    message = (
        f"\n【🔥 お買い得品を検出しました！ ({dummy_item['discount_pct']}% OFF)】\n"
        f"🌟 商品名  : {dummy_item['name']}\n"
        f"💰 販売価格: {dummy_item['price']:,}円\n"
        f"📊 相場平均: {dummy_item['average_price']:,}円 (差額: -{difference:,}円)\n"
        f"✨ 状態    : {dummy_item['status']} | 店舗: {dummy_item['shop_name']}\n"
        f"🔗 商品URL : {dummy_item['url']}\n"
    )

    # 4. LINEにテスト通知を送信します
    success = notifier.send_notification(message)
    
    if success:
        logger.info("=== LINEへのテストプッシュメッセージ送信が正常に完了しました！ ===")
    else:
        logger.error("=== LINEへのメッセージ送信に失敗しました。config.jsonの設定を確認してください。 ===")

if __name__ == "__main__":
    test_notification()
