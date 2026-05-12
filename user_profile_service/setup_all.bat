@echo off
title 🚀 Fully Auto Setup (No Prompt)

echo =========================================
echo 🚀 AUTO SETUP STARTED (NO PASSWORD ASK)
echo =========================================

REM ===============================
REM CONFIG (SET YOUR DB USER HERE)
REM ===============================
set DB_USER=root
set DB_PASS=Gaurav@123
set DB_NAME=abt_dev

REM ===============================
REM 1. CREATE VENV
REM ===============================
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate

REM ===============================
REM 2. INSTALL REQUIREMENTS
REM ===============================
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install Python requirements.
    pause
    exit /b 1
)

REM ===============================
REM 3. CREATE .env
REM ===============================
if not exist .env (
    python -c "open('.env','w', encoding='utf-8').write('DATABASE_URL=mysql+pymysql://root:Gaurav%%40123@localhost:3306/abt_dev\nDB_USER=root\nDB_PASSWORD=Gaurav@123\nDB_HOST=localhost\nDB_PORT=3306\nDB_NAME=abt_dev\n')"
)

REM ===============================
REM 4. CREATE DATABASE (NO ROOT)
REM ===============================
echo 🗄️ Creating database using app user...

mysql -u %DB_USER% -p%DB_PASS% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME%;"

if %errorlevel% neq 0 (
    echo ❌ FAILED: Check DB_USER / DB_PASS
    echo 👉 You must create this user once manually
    pause
    exit /b
)

REM ===============================
REM 5. RUN SQL
REM ===============================
mysql -u %DB_USER% -p%DB_PASS% %DB_NAME% < user_profile_service.sql

REM ===============================
REM 6. RUN SERVER
REM ===============================
echo Starting server on port 8009...
uvicorn app.main:app --reload --port 8009

pause
