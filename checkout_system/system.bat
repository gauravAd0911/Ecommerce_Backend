@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
title ShopFlow Setup

echo.
echo  ShopFlow — Guest Checkout with Dual OTP
echo  ========================================
echo.

:: ── Config ───────────────────────────────────────────────────
SET VENV=venv
SET HOST=127.0.0.1
SET PORT=8004
IF "%MYSQL_ROOT_USER%"==""     SET MYSQL_ROOT_USER=root
IF "%MYSQL_ROOT_PASSWORD%"=="" SET MYSQL_ROOT_PASSWORD=Gaurav@123

:: ── 1. Python ─────────────────────────────────────────────────
echo [1/6] Checking Python...
python --version >nul 2>&1 || (echo ERROR: Python 3.10+ not found. & pause & exit /b 1)
FOR /f "tokens=2 delims= " %%v IN ('python --version 2^>^&1') DO echo  OK: Python %%v

:: ── 2. Virtual environment ────────────────────────────────────
echo [2/6] Virtual environment...
IF NOT EXIST "%VENV%\Scripts\activate.bat" (
    python -m venv %VENV% || (echo ERROR: venv failed. & pause & exit /b 1)
    echo  Created: .\%VENV%\
) ELSE ( echo  Exists: .\%VENV%\ )
CALL "%VENV%\Scripts\activate.bat"

:: ── 3. Dependencies ───────────────────────────────────────────
echo [3/6] Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q || (echo ERROR: pip install failed. & pause & exit /b 1)
echo  OK: All packages installed.

:: ── 4. .env ───────────────────────────────────────────────────
echo [4/6] Environment file...
IF NOT EXIST ".env" (
    copy /Y ".env" ".env" >nul 2>&1
    echo  Created: .env
) ELSE ( echo  Exists: .env )

:: ── 5. Database ───────────────────────────────────────────────
echo [5/6] MySQL database setup...
WHERE mysql >nul 2>&1
IF ERRORLEVEL 1 (
    echo  SKIP: mysql not in PATH. Run manually: mysql -u root -p ^< setup_db.sql
) ELSE (
    IF "%MYSQL_ROOT_PASSWORD%"=="" (
        mysql -u %MYSQL_ROOT_USER% -p < setup_db.sql
    ) ELSE (
        mysql -u %MYSQL_ROOT_USER% -p%MYSQL_ROOT_PASSWORD% < setup_db.sql
    )
    IF ERRORLEVEL 1 (echo  WARN: DB setup had errors. Check MySQL is running.) ELSE (echo  OK: Database ready.)
)

:: ── 6. Launch ─────────────────────────────────────────────────
echo [6/6] Starting server...
echo.
echo  Storefront : http://%HOST%:%PORT%
echo  API Docs   : http://%HOST%:%PORT%/docs
echo  Press Ctrl+C to stop.
echo.
uvicorn app.main:app --host %HOST% --port %PORT% --reload
ENDLOCAL