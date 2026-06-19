"""
案件自動検知パイプラインの統括スクリプトです。
クラウドワークス巡回 → Gemini AI判定 → Notion保存 → LINE通知の
全工程を一気通貫で全自動実行します。

既存の main.py（MacBook価格監視）とは完全に分離した独立スクリプトとして設計しています。

使い方:
    python job_hunter.py                    # 通常実行（巡回 + 判定 + 保存 + 通知）
    python job_hunter.py --dry-run          # テスト実行（巡回 + 判定のみ、保存・通知なし）
    python job_hunter.py --keywords "React" # カスタムキーワードで巡回
"""

import argparse
import logging
import os
import sys
from typing import Optional

# .envファイルのパス
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _load_env(key: str) -> Optional[str]:
    """Snitch直下の.envファイルから指定キーの値を読み込みます。"""
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip()
        except Exception:
            pass
    return None


def main():
    """
    案件自動検知パイプラインのメインエントリーポイントです。

    処理フロー:
    1. クラウドワークス公開案件をPlaywrightで巡回（crawler）
    2. 新着案件のみをフィルタリング（crawled_jobs.jsonで重複排除）
    3. 各新着案件をGemini APIに投げて適合度を判定（evaluator）
    4. スコア3以上の案件をNotion DBに保存（exporter）
    5. スコア4以上の「合格」案件をLINEにプッシュ通知（notifier）
    6. 日報サマリーをLINEに送信
    """
    parser = argparse.ArgumentParser(
        description="クラウドワークスの公開案件を自動巡回し、AI適合度判定・Notion保存・LINE通知を行います。"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="検索キーワード（カンマ区切り）。未指定時は.envのJOB_SEARCH_KEYWORDSを使用"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="テスト実行モード（巡回とAI判定のみ行い、Notion保存とLINE通知はスキップ）"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="ブラウザをヘッドレスモードで起動（デフォルト: True）"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="ブラウザを画面表示モードで起動（デバッグ用）"
    )

    args = parser.parse_args()

    # ヘッドレスモードの決定
    headless = not args.no_headless

    # キーワードの決定
    if args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]
    else:
        env_keywords = _load_env("JOB_SEARCH_KEYWORDS")
        if env_keywords:
            keywords = [kw.strip() for kw in env_keywords.split(",") if kw.strip()]
        else:
            keywords = ["Python スクレイピング", "Python 自動化", "バナー制作", "バナー画像作成"]

    dry_run = args.dry_run

    logger.info("=" * 60)
    logger.info("🚀 Snitch 案件自動検知パイプラインを開始します")
    logger.info(f"   検索キーワード: {keywords}")
    logger.info(f"   ヘッドレスモード: {headless}")
    logger.info(f"   テスト実行: {dry_run}")
    logger.info("=" * 60)

    # 各モジュールの初期化
    from crawler import CrowdWorksCrawler
    from evaluator import JobEvaluator
    from exporter import NotionExporter

    crawler = CrowdWorksCrawler(headless=headless)
    evaluator = JobEvaluator()
    exporter = NotionExporter()

    errors = []

    # ==========================================
    # ステップ 1: クラウドワークス公開案件の巡回
    # ==========================================
    logger.info("=== [ステップ 1] クラウドワークスの公開案件を巡回します ===")
    try:
        new_jobs = crawler.crawl(keywords=keywords)
    except Exception as crawl_error:
        logger.error(f"巡回中に致命的なエラーが発生しました: {crawl_error}")
        errors.append(f"クローラーエラー: {crawl_error}")
        new_jobs = []

    total_crawled = len(new_jobs)
    logger.info(f"巡回完了: 新着 {total_crawled} 件の案件を取得しました。")

    if not new_jobs:
        logger.info("新着案件がないため、AI判定をスキップします。")
        if not dry_run:
            exporter.send_summary(total_crawled=0, total_evaluated=0, passed_count=0, errors=errors)
        logger.info("=" * 60)
        return

    # ==========================================
    # ステップ 2: Gemini APIによるAI適合度判定
    # ==========================================
    logger.info("=== [ステップ 2] 新着案件のAI適合度判定を実行します ===")
    evaluated_jobs = []

    # API無料枠の制限を保護するため、1回あたりの最大判定件数を5件に制限
    MAX_EVALUATIONS_PER_RUN = 5
    jobs_to_evaluate = new_jobs[:MAX_EVALUATIONS_PER_RUN]
    if len(new_jobs) > MAX_EVALUATIONS_PER_RUN:
        logger.info(f"新着案件が多数検出されたため、今回は最新の {MAX_EVALUATIONS_PER_RUN} 件のみ判定します。")

    for i, job in enumerate(jobs_to_evaluate):
        logger.info(f"--- 判定 {i + 1}/{len(jobs_to_evaluate)}: 「{job.get('title', '不明')[:50]}」 ---")
        try:
            evaluation = evaluator.evaluate(job)
            if evaluation:
                evaluated_jobs.append({"job": job, "evaluation": evaluation})
            else:
                logger.warning(f"AI判定がNoneを返しました（スキップ）")
        except Exception as eval_error:
            logger.error(f"AI判定中にエラーが発生しました: {eval_error}")
            errors.append(f"AI判定エラー ({job.get('title', '不明')[:30]}): {eval_error}")

    total_evaluated = len(evaluated_jobs)
    logger.info(f"AI判定完了: {total_evaluated}/{total_crawled} 件を評価しました。")

    # 判定結果のコンソール出力（一覧表示）
    logger.info("------------- AI判定結果一覧 -------------")
    for entry in sorted(evaluated_jobs, key=lambda x: x["evaluation"]["score"], reverse=True):
        ev = entry["evaluation"]
        jb = entry["job"]
        logger.info(
            f"{'⭐' * ev['score']} スコア {ev['score']}/5 | {ev['decision']} | "
            f"{jb.get('title', '不明')[:50]} | {jb.get('budget', '不明')}"
        )
    logger.info("-------------------------------------------")

    if dry_run:
        logger.info("🏁 テスト実行モードのため、Notion保存とLINE通知はスキップします。")
        logger.info("=" * 60)
        return

    # ==========================================
    # ステップ 3: Notion DBへの保存 & LINE通知
    # ==========================================
    logger.info("=== [ステップ 3] 判定結果の保存と通知を実行します ===")
    passed_count = 0

    for entry in evaluated_jobs:
        job = entry["job"]
        evaluation = entry["evaluation"]
        score = evaluation.get("score", 0)

        # スコア3以上はNotionに保存（分析・振り返り用）
        if score >= 3:
            try:
                exporter.save_to_notion(job, evaluation)
            except Exception as save_error:
                logger.error(f"Notion保存中にエラーが発生しました: {save_error}")
                errors.append(f"Notion保存エラー: {save_error}")

        # スコア4以上（合格判定）はLINEにプッシュ通知
        if score >= 4:
            passed_count += 1
            try:
                exporter.notify_line(job, evaluation)
            except Exception as notify_error:
                logger.error(f"LINE通知中にエラーが発生しました: {notify_error}")
                errors.append(f"LINE通知エラー: {notify_error}")

    # ==========================================
    # ステップ 4: 日報サマリーの送信
    # ==========================================
    logger.info("=== [ステップ 4] 日報サマリーをLINEに送信します ===")
    exporter.send_summary(
        total_crawled=total_crawled,
        total_evaluated=total_evaluated,
        passed_count=passed_count,
        errors=errors
    )

    logger.info("=" * 60)
    logger.info(f"🏁 案件自動検知パイプライン完了 (新着: {total_crawled} / 判定: {total_evaluated} / 合格: {passed_count})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
