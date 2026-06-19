@echo off
REM ============================================================
REM  Snitch - Automated Daily Execution Script
REM  Called by Windows Task Scheduler to check deals and notify.
REM ============================================================

cd /d "s:\00_Apps\01_Projects\Snitch"

"s:\00_Apps\01_Projects\Snitch\.venv\Scripts\python.exe" main.py MacBook --threshold 10

echo [%date% %time%] Snitch done >> "s:\00_Apps\01_Projects\Snitch\snitch_log.txt"
