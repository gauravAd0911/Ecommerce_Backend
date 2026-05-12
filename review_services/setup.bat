@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Review Service Setup ^& Launch
color 07

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

set "SERVICE_NAME=review_service"
set "REQUIREMENTS=requirements.txt"
set "SCHEMA_FILE=schema.sql"
set "ENV_FILE=.env"
set "APP_MODULE=app.main:app"
set "HOST=127.0.0.1"
set "PORT=8008"
set "LOG_LEVEL=info"
set "VENV_DIR=venv"
set "VENV_PYTHON="

if not exist "%VENV_DIR%\Scripts\python.exe" if exist ".venv\Scripts\python.exe" (
    set "VENV_DIR=.venv"
)

echo.
echo  ============================================================
echo   Review Service Automated Setup ^& Launch
echo  ============================================================
echo.

call :log_step "0" "Checking working directory"

if not exist "%REQUIREMENTS%" (
    call :log_error "requirements.txt not found."
    pause
    exit /b 1
)

if not exist "%SCHEMA_FILE%" (
    call :log_error "%SCHEMA_FILE% not found."
    echo   Expected location: %PROJECT_ROOT%%SCHEMA_FILE%
    pause
    exit /b 1
)

call :log_ok "Working directory looks correct."

call :log_step "1" "Checking Python installation"

where python >nul 2>&1
if errorlevel 1 (
    call :log_error "python not found on PATH."
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
call :log_ok "Found Python %PY_VERSION%"

call :log_step "2" "Checking MySQL client"

where mysql >nul 2>&1
if errorlevel 1 (
    call :log_error "mysql.exe not found on PATH."
    pause
    exit /b 1
)

call :log_ok "MySQL client found."

call :log_step "3" "Preparing virtual environment"

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo   [INFO] Existing virtual environment found in %VENV_DIR%.
) else (
    echo   [INFO] Creating virtual environment in %VENV_DIR%...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        call :log_error "Failed to create virtual environment."
        pause
        exit /b 1
    )
)

set "VENV_PYTHON=%PROJECT_ROOT%%VENV_DIR%\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    call :log_error "Virtual environment Python executable not found."
    pause
    exit /b 1
)

call :log_ok "Virtual environment ready."

call :log_step "4" "Installing dependencies"

"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
"%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS%" --quiet
if errorlevel 1 (
    call :log_error "Dependency installation failed."
    pause
    exit /b 1
)

call :log_ok "All packages installed."

call :log_step "5" "Loading environment configuration"

if not exist "%ENV_FILE%" (
    call :log_error ".env not found."
    echo   Create .env first or rerun after adding DB credentials.
    pause
    exit /b 1
)

call :parse_env
call :log_ok ".env loaded."

call :log_step "6" "Creating database and applying schema"

mysql -h !_DB_HOST! -P !_DB_PORT! -u !_DB_USER! --password=!_DB_PASSWORD! -e "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    call :log_error "Cannot connect to MySQL with values from .env."
    pause
    exit /b 1
)

mysql -h !_DB_HOST! -P !_DB_PORT! -u !_DB_USER! --password=!_DB_PASSWORD! -e "CREATE DATABASE IF NOT EXISTS !_DB_NAME! CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
    call :log_error "Failed to create database '!_DB_NAME!'."
    echo   MySQL returned an error while creating the database.
    pause
    exit /b 1
)

mysql -h !_DB_HOST! -P !_DB_PORT! -u !_DB_USER! --password=!_DB_PASSWORD! !_DB_NAME! < "%SCHEMA_FILE%"
if errorlevel 1 (
    call :log_error "Failed to apply %SCHEMA_FILE%."
    echo   Inspect the MySQL output above for the exact schema error.
    pause
    exit /b 1
)

call :log_ok "Schema applied successfully."

call :log_step "7" "Starting Uvicorn server"

set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"

echo.
echo  ============================================================
echo   Project root : %PROJECT_ROOT%
echo   Server       : http://%HOST%:%PORT%
echo   Docs         : http://%HOST%:%PORT%/docs
echo   Python       : %VENV_PYTHON%
echo   Press Ctrl+C to stop
echo  ============================================================
echo.

"%VENV_PYTHON%" -m uvicorn "%APP_MODULE%" --host "%HOST%" --port "%PORT%" --log-level "%LOG_LEVEL%" --reload
if errorlevel 1 (
    call :log_error "Uvicorn exited with an error."
    pause
    exit /b 1
)

endlocal
exit /b 0

:log_step
echo.
echo  [STEP %~1] %~2
echo  ------------------------------------------------------------
goto :eof

:log_ok
echo   [OK]    %~1
goto :eof

:log_error
echo.
echo  [ERROR] %~1
echo.
goto :eof

:parse_env
for /f "usebackq tokens=1,* delims==" %%k in ("%ENV_FILE%") do (
    set "_LINE=%%k"
    if not "!_LINE:~0,1!"=="#" if not "!_LINE!"=="" (
        set "_%%k=%%l"
    )
)
goto :eof
