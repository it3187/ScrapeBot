import os
import json
import datetime
import requests
import feedparser
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [ScrapeBot] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 保存先ファイルの定義
OUTPUT_DIR = "s:\\00_Apps\\10_AgyManager\\data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "trends.json")

def fetch_yahoo_trends():
    """Yahoo!ニュース RSSから最新トピックスを取得します"""
    rss_url = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
    logger.info("Yahoo!ニュース RSSからデータ取得中...")
    try:
        feed = feedparser.parse(rss_url)
        trends = []
        for entry in feed.entries[:5]:
            trends.append({
                "title": entry.title,
                "url": entry.link,
                "source": "Yahoo!ニュース"
            })
        return trends
    except Exception as e:
        logger.error(f"Yahoo!ニュース取得失敗: {e}")
        return []

def fetch_v2ex_trends():
    """V2EX Hot Topics APIから人気スレッドを取得します"""
    url = "https://www.v2ex.com/api/topics/hot.json"
    headers = {"User-Agent": "agent-reach/1.0"}
    logger.info("V2EX APIからデータ取得中...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            trends = []
            for topic in response.json()[:5]:
                trends.append({
                    "title": topic.get("title"),
                    "url": topic.get("url"),
                    "source": "V2EX"
                })
            return trends
        else:
            logger.error(f"V2EX取得失敗: HTTP {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"V2EX取得失敗: {e}")
        return []

def main():
    logger.info("=== トレンドデータ収集を開始します ===")
    
    # ディレクトリ作成
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    trends = []
    
    # 1. Yahoo!ニュース RSS
    trends.extend(fetch_yahoo_trends())
    
    # 2. V2EX Hot
    trends.extend(fetch_v2ex_trends())
    
    # 最終的なデータ構造
    result = {
        "timestamp": datetime.datetime.now().isoformat(),
        "trends": trends
    }
    
    # JSON保存
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ トレンドデータを保存しました: {OUTPUT_FILE} (合計 {len(trends)} 件)")
    except Exception as e:
        logger.error(f"ファイル保存失敗: {e}")

if __name__ == "__main__":
    main()
