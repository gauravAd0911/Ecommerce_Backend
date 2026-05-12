@echo off
SETLOCAL

echo =====================================
echo   INVENTORY SERVICE SETUP STARTING
echo =====================================

:: Step 1 - Check .env exists
IF NOT EXIST .env (
    echo [ERROR] .env file not found!
    goto :error
)

:: Step 2 - Load ENV variables
echo [INFO] Loading environment variables...
for /f "tokens=1,* delims==" %%A in (.env) do (
    if not "%%A"=="" (
        if not "%%A:~0,1"=="#" (
            set %%A=%%B
        )
    )
)

echo DB_USER=%DB_USER%
echo DB_NAME=%DB_NAME%

:: Step 3 - Create venv
IF NOT EXIST venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv || goto :error
)

:: Step 4 - Activate venv
call venv\Scripts\activate || goto :error

:: Step 5 - Install deps
echo [INFO] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :error

:: Step 6 - Check MySQL
where mysql >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] MySQL CLI not found in PATH
    goto :error
)

:: Step 7 - Create DB
echo [INFO] Creating database...
mysql -u %DB_USER% -p%DB_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME%;" || goto :error

:: =====================================================
:: ALEMBIC AUTO SETUP
:: =====================================================

:: Step 8 - Initialize Alembic if not exists
IF NOT EXIST alembic (
    echo [INFO] Initializing Alembic...
    alembic init alembic || goto :error
)

:: Step 9 - Ensure alembic.ini exists
IF NOT EXIST alembic.ini (
    echo [ERROR] alembic.ini missing!
    goto :error
)

:: Step 10 - Ensure at least one migration exists
IF NOT EXIST alembic\versions (
    mkdir alembic\versions
)

:: Check if versions folder is empty
dir /b alembic\versions >nul 2>nul
IF ERRORLEVEL 1 (
    echo [INFO] Creating initial migration...
    alembic revision --autogenerate -m "initial" || goto :error
)

:: Step 11 - Run migrations
echo [INFO] Running migrations...
alembic upgrade head || goto :error

:: =====================================================
:: START SERVER
:: =====================================================

:: Defaults
IF "%HOST%"=="" SET HOST=127.0.0.1
SET PORT=8005

echo [INFO] Starting server...
set PYTHONPATH=.
uvicorn app.main:app --host %HOST% --port %PORT% --reload

goto :end

:error
echo.
echo [FAILED] Setup failed.
pause
exit /b 1

:end
echo.
echo [SUCCESS]
pause
ENDLOCAL