@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

:: NBA Matchup Predictor Automation Script
:: This script provides options to update data or start the automation scheduler

echo ==========================================
echo    NBA Matchup Predictor Control Panel
echo ==========================================

set /p USER_DATE="Upcoming Game Date (dd/mm/yyyy, or press Enter for today): "
set DATE_ARG=
if not "!USER_DATE!" == "" (
    set DAY=!USER_DATE:~0,2!
    set MONTH=!USER_DATE:~3,2!
    set YEAR=!USER_DATE:~6,4!
    set TARGET_DATE=!YEAR!-!MONTH!-!DAY!
    set DATE_ARG=--date !TARGET_DATE!
    echo [INFO] Target date set to !TARGET_DATE!
)

echo.
echo 1. Run Full AI Pipeline (Fetch Quarters + Injuries + Odds + Export)
echo 2. Start Daily Scheduler (Runs every day at 06:00)
echo 3. Just Open Dashboard
echo 4. Fetch Latest Betting Odds (odds-api.io)
echo 5. Exit
echo ==========================================
set /p CHOICE="Select an option (1-5): "

if "%CHOICE%" == "1" (
    echo [INFO] Running update pipeline...
    python pipeline_scheduler.py --now !DATE_ARG!
    echo.
    echo [PROCESS COMPLETE] Check above for errors.
    if exist index.html (
        echo [INFO] Opening dashboard...
        start index.html
    ) else (
        echo [WARNING] index.html not found.
    )
    pause
)

if "%CHOICE%" == "2" (
    echo [INFO] Starting daily scheduler...
    python pipeline_scheduler.py
)

if "%CHOICE%" == "3" (
    echo [INFO] Opening dashboard...
    start index.html
)

if "%CHOICE%" == "4" (
    echo [INFO] Fetching latest betting odds...
    python fetch_odds.py
    pause
)

if "%CHOICE%" == "5" (
    exit /b 0
)

echo.
echo Done.
pause
