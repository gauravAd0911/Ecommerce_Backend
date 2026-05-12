@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ================================
echo ORDER SERVICE SETUP STARTED
echo ================================

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

set "ENV_FILE=%PROJECT_DIR%\.env"

if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
        set "_k=%%a"
        set "_v=%%b"
        if not "!_k!"=="" if not "!_k:~0,1!"=="#" set "!_k!=!_v!"
    )
)

if not defined DB_HOST set "DB_HOST=localhost"
if not defined DB_PORT set "DB_PORT=3306"
if not defined DB_NAME set "DB_NAME=abt_dev"
if not defined DB_USER set "DB_USER=root"
if not defined DB_PASS set "DB_PASS="
if not defined APP_HOST set "APP_HOST=127.0.0.1"
if not defined APP_PORT set "APP_PORT=8007"
if not defined JWT_SECRET set "JWT_SECRET=your-super-secret-jwt-key-change-in-production"
if not defined JWT_ALGORITHM set "JWT_ALGORITHM=HS256"

if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python virtual environment.
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate Python virtual environment.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

where mysql >nul 2>&1
if errorlevel 1 (
    echo [WARN] mysql.exe not found on PATH. Skipping schema import.
    goto :start_server
)

echo Creating database schema...
set "MYSQL_ARGS=-h %DB_HOST% -P %DB_PORT% -u %DB_USER% --protocol=TCP"
if not "%DB_PASS%"=="" set "MYSQL_ARGS=%MYSQL_ARGS% -p%DB_PASS%"

mysql %MYSQL_ARGS% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
    echo [WARN] Could not create or verify database. Check MySQL credentials in .env.
    goto :start_server
)

if exist schemas.sql (
    mysql %MYSQL_ARGS% "%DB_NAME%" < schemas.sql
    if errorlevel 1 echo [WARN] Schema import reported errors. Server will still start.
) else (
    echo [WARN] schemas.sql not found. Skipping schema import.
)

:start_server
echo Starting order service on http://%APP_HOST%:%APP_PORT%
uvicorn app.main:app --reload --host "%APP_HOST%" --port "%APP_PORT%"

if errorlevel 1 (
    echo [ERROR] Uvicorn exited with an error.
    pause
    exit /b 1
)

endlocal
