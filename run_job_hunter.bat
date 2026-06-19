@echo off
REM ============================================================
REM  ScrapeBot Job Hunter - 案件自動巡回パイプライン実行スクリプト
REM  クラウドワークスの公開案件を巡回 → AI判定 → Notion保存 → LINE通知
REM ============================================================

cd /d "s:\00_Apps\01_Projects\ScrapeBot"

"s:\00_Apps\01_Projects\ScrapeBot\.venv\Scripts\python.exe" job_hunter.py

echo [%date% %time%] Job Hunter done >> "s:\00_Apps\01_Projects\ScrapeBot\scrapebot_log.txt"
