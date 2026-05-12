@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo =========================================
echo FULL PROJECT AUTO SETUP STARTED
echo =========================================

set "ROOT=%CD%"
set "VENV_DIR=%ROOT%\venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "ENV_FILE=%ROOT%\.env"
set "REQ_FILE=%ROOT%\requirements.txt"
set "SCHEMA_FILE=%ROOT%\schema.sql"

set "DB_NAME=auth_m2_db"
set "DB_USER=root"
set "DB_PASS=Gaurav@123"
set "DB_HOST=127.0.0.1"
set "DB_PORT=3306"
set "DB_URL=mysql+pymysql://%DB_USER%:%DB_PASS%@%DB_HOST%:%DB_PORT%/%DB_NAME%"
set "MYSQL_EXE=mysql"

REM 1) Create venv
if not exist "%VENV_PY%" (
  echo Creating virtual environment...
  py -3.11 -m venv "%VENV_DIR%"
)

if not exist "%VENV_PY%" (
  echo [ERROR] venv python not found: %VENV_PY%
  pause
  exit /b 1
)

REM Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

REM 2) Install requirements
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail

if exist "%REQ_FILE%" (
  echo Installing requirements...
  "%VENV_PY%" -m pip install -r "%REQ_FILE%"
  if errorlevel 1 goto :fail
) else (
  echo [ERROR] requirements.txt not found
  goto :fail
)

REM 3) Ensure .env points to dedicated DB
if not exist "%ENV_FILE%" (
  echo Creating .env...
  > "%ENV_FILE%" (
    echo DATABASE_URL=%DB_URL%
    echo.
    echo JWT_SECRET=your-super-secret-jwt-key-change-in-production
    echo.
    echo TWILIO_ACCOUNT_SID=PASTE_YOUR_SID
    echo TWILIO_AUTH_TOKEN=PASTE_YOUR_TOKEN
    echo TWILIO_PHONE_NUMBER=PASTE_YOUR_NUMBER
    echo.
    echo OTP_EXPIRY_MINUTES=5
  )
) else (
  REM Simple safe replace if it still points at abt_dev
  powershell -Command "(Get-Content '%ENV_FILE%') -replace '/abt_dev', '/%DB_NAME%' | Set-Content '%ENV_FILE%'"
)

echo .env ready

REM 4) Create DB and apply schema.sql (no Alembic)
where %MYSQL_EXE% >nul 2>nul
if errorlevel 1 (
  echo [ERROR] mysql.exe not found in PATH
  goto :fail
)

echo Creating database if not exists...
%MYSQL_EXE% -u %DB_USER% -p%DB_PASS% -h %DB_HOST% -P %DB_PORT% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME%;"
if errorlevel 1 goto :fail

echo Applying schema.sql...
if not exist "%SCHEMA_FILE%" (
  echo [ERROR] schema.sql not found: %SCHEMA_FILE%
  goto :fail
)

%MYSQL_EXE% -u %DB_USER% -p%DB_PASS% -h %DB_HOST% -P %DB_PORT% < "%SCHEMA_FILE%"
if errorlevel 1 goto :fail

echo Schema applied.

REM 5) Run server using venv python (avoids wrong venv)
echo Starting FastAPI server...
"%VENV_PY%" -m uvicorn auth.main:app --reload --port 8001

pause
exit /b 0

:fail
echo.
echo SETUP FAILED
pause
exit /b 1
