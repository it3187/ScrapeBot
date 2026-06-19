"""
クラウドワークスの公開案件一覧ページを Playwright で巡回し、
案件情報（タイトル、予算、URL、概要）を自動抽出するクローラーです。

意図: ログイン不要の公開ページのみを巡回することで、利用規約リスクを最小化しつつ
      新着案件を効率的に収集します。
"""

import os
import json
import time
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 日本標準時（JST）のタイムゾーン定義
JST = timezone(timedelta(hours=9))

# 巡回済み案件の永続化ファイルパス
CRAWLED_JOBS_FILE = "s:\\00_Apps\\10_AgyManager\\data\\crawled_jobs.json"



class CrowdWorksCrawler:
    """
    クラウドワークスの公開案件検索ページを Playwright（ヘッドレスブラウザ）で
    自動巡回し、案件メタデータを構造化して返すクローラーです。
    """

    # クラウドワークスの公開案件検索ベースURL
    BASE_SEARCH_URL = "https://crowdworks.jp/public/jobs/search"

    def __init__(self, headless: bool = True, min_delay: float = 3.0, max_delay: float = 6.0, max_retries: int = 3):
        """
        クローラーの初期設定を行います。

        Args:
            headless: ブラウザをヘッドレスモード（画面なし）で起動するかどうか
            min_delay: ページ遷移間の最小待機秒数（サーバー負荷軽減のため）
            max_delay: ページ遷移間の最大待機秒数
            max_retries: エラー時の最大リトライ回数
        """
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self._crawled_urls = self._load_crawled_urls()

    def _load_crawled_urls(self) -> set:
        """
        過去に巡回済みのURL一覧をファイルから読み込みます。
        重複した案件をGemini APIに送らないためのキャッシュとして機能します。
        """
        if os.path.exists(CRAWLED_JOBS_FILE):
            try:
                with open(CRAWLED_JOBS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("crawled_urls", []))
            except Exception as load_error:
                logger.warning(f"巡回済みURLファイルの読み込みに失敗しました（新規作成します）: {load_error}")
        return set()

    def _save_crawled_urls(self):
        """巡回済みURL一覧をファイルに永続化します。"""
        try:
            with open(CRAWLED_JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump({"crawled_urls": list(self._crawled_urls)}, f, ensure_ascii=False, indent=2)
        except Exception as save_error:
            logger.error(f"巡回済みURLファイルの保存に失敗しました: {save_error}")

    def _safe_sleep(self):
        """サーバーに負荷をかけないためのランダムなスリープを実行します。"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"安全のために {delay:.1f} 秒間待機します...")
        time.sleep(delay)

    def crawl(self, keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        指定されたキーワード群でクラウドワークスの公開案件を巡回し、
        新着の案件情報をリスト形式で返します。

        Args:
            keywords: 検索キーワードのリスト（例: ["Python スクレイピング", "バナー制作"]）

        Returns:
            新着案件データのリスト。各案件は以下のキーを持つ辞書:
            {
                "title": "案件名",
                "url": "詳細ページURL",
                "budget": "予算・報酬",
                "description": "案件の概要",
                "category": "カテゴリ",
                "extracted_at": "ISO8601形式の取得日時"
            }
        """
        if keywords is None:
            keywords = ["Python スクレイピング"]

        all_jobs = []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwrightがインストールされていません。pip install playwright && playwright install chromium を実行してください。")
            return []

        with sync_playwright() as p:
            # Chromiumブラウザを起動（ヘッドレスモードで軽量に動作）
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="ja-JP"
            )
            page = context.new_page()

            for keyword in keywords:
                logger.info(f"=== キーワード「{keyword}」で案件を巡回中 ===")
                jobs_for_keyword = self._crawl_keyword(page, keyword)
                all_jobs.extend(jobs_for_keyword)
                logger.info(f"「{keyword}」から新着 {len(jobs_for_keyword)} 件を取得しました。")

            browser.close()

        # 巡回済みURLを永続化
        self._save_crawled_urls()

        logger.info(f"巡回完了: 全キーワード合計で新着 {len(all_jobs)} 件の案件を取得しました。")
        return all_jobs

    def _crawl_keyword(self, page, keyword: str) -> List[Dict[str, Any]]:
        """
        1つのキーワードでクラウドワークスの検索結果を巡回し、案件情報を抽出します。

        意図: キーワードごとにページを分けて巡回することで、
             取得漏れを防ぎつつサーバーへの負荷を最小限に抑えます。
        """
        jobs = []

        for attempt in range(1, self.max_retries + 1):
            try:
                search_url = f"{self.BASE_SEARCH_URL}?keyword={keyword}"
                logger.info(f"アクセス中 (試行 {attempt}/{self.max_retries}): {search_url}")
                self._safe_sleep()

                page.goto(search_url, timeout=30000)
                # 案件リストのDOM要素が表示されるまで待機（networkidleだと止まらないケースがあるため）
                page.wait_for_selector(".job_listing, .jobs_show, .job-search-results, [class*='JobOffer'], [class*='job']", timeout=15000)

                # 案件カード要素をすべて取得する
                # クラウドワークスはページ構成を変えることがあるため、複数のセレクタを試行する
                job_elements = page.query_selector_all(".job_offer_list li, .jobs_show_list li, [class*='JobOfferList'] a, .job-search-results .job-item")

                if not job_elements:
                    # フォールバック: より汎用的なセレクタで探す
                    job_elements = page.query_selector_all("a[href*='/public/jobs/']")
                    logger.info(f"フォールバックセレクタで {len(job_elements)} 件の候補を検出しました。")

                logger.info(f"検索結果から {len(job_elements)} 件の候補を検出しました。パースを開始します。")

                for element in job_elements:
                    try:
                        job_data = self._parse_job_element(page, element)
                        if job_data and job_data["url"] not in self._crawled_urls:
                            jobs.append(job_data)
                            self._crawled_urls.add(job_data["url"])
                    except Exception as parse_error:
                        logger.debug(f"個別案件のパースに失敗しました（スキップ）: {parse_error}")
                        continue

                # 成功したのでリトライループを抜ける
                break

            except Exception as page_error:
                logger.warning(f"ページの取得に失敗しました (試行 {attempt}/{self.max_retries}): {page_error}")
                if attempt < self.max_retries:
                    # 指数バックオフで待機してリトライ
                    backoff_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"指数バックオフ: {backoff_time:.1f} 秒後にリトライします...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"キーワード「{keyword}」の巡回を全リトライ失敗のため断念します。")

        return jobs

    def _parse_job_element(self, page, element) -> Optional[Dict[str, Any]]:
        """
        案件のDOM要素から、タイトル・URL・予算・概要を抽出して辞書で返します。

        意図: クラウドワークスのHTML構造が変更される可能性を考慮し、
             複数のセレクタパターンで柔軟に情報抽出を試みます。
        """
        # URL抽出（最も確実な情報）
        href = element.get_attribute("href")
        if not href:
            link = element.query_selector("a[href*='/public/jobs/']")
            if link:
                href = link.get_attribute("href")
        if not href or "/public/jobs/" not in href:
            return None

        # 絶対URLに変換
        url = href if href.startswith("http") else f"https://crowdworks.jp{href}"
        # URLからクエリパラメータを除去して正規化（重複検出の精度向上のため）
        url = url.split("?")[0]

        # 案件詳細ページURL（末尾が数字のID）のみを対象とする
        import re
        if not re.search(r'/public/jobs/\d+$', url):
            return None

        # タイトル抽出
        title = ""
        title_selectors = [
            "h3", "h4", ".job_offer_detail_title", ".ttl_job",
            "[class*='title']", "[class*='Title']", "a"
        ]
        for selector in title_selectors:
            title_el = element.query_selector(selector)
            if title_el:
                title = title_el.inner_text().strip()
                if title and len(title) > 3:
                    break
        if not title:
            title = element.inner_text().strip()[:100]

        # 予算抽出
        budget = ""
        budget_selectors = [
            ".amount", ".price", "[class*='budget']", "[class*='price']",
            "[class*='Budget']", "[class*='Price']", "[class*='reward']"
        ]
        for selector in budget_selectors:
            budget_el = element.query_selector(selector)
            if budget_el:
                budget = budget_el.inner_text().strip()
                if budget:
                    break

        # 概要テキスト抽出
        description = ""
        desc_selectors = [
            ".job_offer_detail_description", ".summary", "[class*='description']",
            "[class*='summary']", "[class*='desc']", "p"
        ]
        for selector in desc_selectors:
            desc_el = element.query_selector(selector)
            if desc_el:
                description = desc_el.inner_text().strip()[:500]
                if description:
                    break

        # カテゴリ抽出
        category = ""
        cat_selectors = [
            ".category", "[class*='category']", "[class*='Category']", ".tag"
        ]
        for selector in cat_selectors:
            cat_el = element.query_selector(selector)
            if cat_el:
                category = cat_el.inner_text().strip()
                if category:
                    break

        return {
            "title": title,
            "url": url,
            "budget": budget,
            "description": description,
            "category": category,
            "extracted_at": datetime.now(JST).isoformat()
        }
