@echo off
REM ============================================================
REM  ScrapeBot - Automated Daily Execution Script
REM  Called by Windows Task Scheduler to check deals and notify.
REM ============================================================

cd /d "c:\Apps\ScrapeBot"

"c:\Apps\ScrapeBot\.venv\Scripts\python.exe" main.py MacBook --threshold 20

echo [%date% %time%] ScrapeBot done >> "c:\Apps\ScrapeBot\scrapebot_log.txt"
