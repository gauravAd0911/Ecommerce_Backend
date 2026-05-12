@echo off
echo =========================================
echo FULL NOTIFICATION SERVICE SETUP STARTED
echo =========================================

REM -------------------------------
REM 1. Create Virtual Environment
REM -------------------------------
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists
)

REM -------------------------------
REM 2. Activate Virtual Environment
REM -------------------------------
call venv\Scripts\activate

REM -------------------------------
REM 3. Install Requirements
REM -------------------------------
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM -------------------------------
REM 4. Create .env File
REM -------------------------------
if not exist .env (
    echo Creating .env file...

    (
    echo DB_HOST=localhost
    echo DB_USER=root
    echo DB_PASSWORD=Gaurav@123
    echo DB_NAME=abt_dev
    echo.
    echo TWILIO_ACCOUNT_SID=your_sid_here
    echo TWILIO_AUTH_TOKEN=your_token_here
    echo TWILIO_PHONE_NUMBER=+1234567890
    ) > .env

    echo .env file created
) else (
    echo .env already exists
)

REM -------------------------------
REM 5. Create Database
REM -------------------------------
echo Creating MySQL database...

mysql -u root -pGaurav@123 -e "CREATE DATABASE IF NOT EXISTS abt_dev;"

IF %ERRORLEVEL% NEQ 0 (
    echo MySQL connection failed. Check username/password.
    pause
    exit /b
)

echo Database ready

REM -------------------------------
REM 6. Run FastAPI Server
REM -------------------------------
echo Starting FastAPI server on port 8011...
echo Tables will be created automatically on startup if they do not exist.

uvicorn app.main:app --reload --port 8011

pause
