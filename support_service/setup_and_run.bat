@echo off
cd /d "%~dp0"
echo =========================================
echo 🚀 SUPPORT SERVICE AUTO SETUP STARTED
echo =========================================

REM ==============================
REM 1. Create Virtual Environment
REM ==============================
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
) else (
    echo ✅ Virtual environment already exists
)

REM ==============================
REM 2. Activate Virtual Environment
REM ==============================
call venv\Scripts\activate

REM ==============================
REM 3. Install Requirements
REM ==============================
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM ==============================
REM 4. Create .env File
REM ==============================
if not exist .env (
    echo ⚙️ Creating .env file...

    (
    echo DB_HOST=localhost
    echo DB_PORT=3306
    echo DB_USER=root
    echo DB_PASSWORD=Gaurav@123
    echo DB_NAME=abt_dev
    echo.
    echo APP_NAME=Support Service
    echo DEBUG=True
    echo JWT_SECRET=your-super-secret-jwt-key-change-in-production
    echo JWT_ALGORITHM=HS256
    ) > .env

    echo ✅ .env created
) else (
    echo ✅ .env already exists
)

REM ==============================
REM 5. Create Database (MySQL)
REM ==============================
echo 🗄️ Creating database if not exists...

mysql -u root -pGaurav@123 -e "CREATE DATABASE IF NOT EXISTS abt_dev;"

IF %ERRORLEVEL% NEQ 0 (
    echo ❌ MySQL command failed. Make sure MySQL is installed and added to PATH.
    pause
    exit /b
)

echo ✅ Database ready

REM ==============================
REM 6. Run SQL Schema
REM ==============================
if exist support_schema.sql (
    echo 📄 Running schema file...
    mysql -u root -pGaurav@123 abt_dev < support_schema.sql
    echo ✅ Tables created
) else (
    echo ⚠️ support_schema.sql not found, skipping...
)

REM ==============================
REM 7. Run FastAPI Server
REM ==============================
echo Starting FastAPI server on port 8010...

uvicorn app.main:app --reload --port 8010

pause
