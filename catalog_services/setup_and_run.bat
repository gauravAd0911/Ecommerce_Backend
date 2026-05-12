@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

:: =============================================================================
::  CATALOG SERVICE — Full Setup & Run Script  (MySQL edition)
::  Automates: venv · requirements · .env · MySQL DB + schema · uvicorn
:: =============================================================================

title Catalog Service — MySQL Setup

:: ── Colour helpers ────────────────────────────────────────────────────────────
set "ESC="
for /f %%a in ('echo prompt $E^| cmd /q') do set "ESC=%%a"
set "CYAN=%ESC%[96m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "RED=%ESC%[91m"
set "BOLD=%ESC%[1m"
set "RESET=%ESC%[0m"

echo.
echo %CYAN%%BOLD%╔══════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%%BOLD%║       CATALOG SERVICE — AUTOMATED SETUP  (MySQL)         ║%RESET%
echo %CYAN%%BOLD%╚══════════════════════════════════════════════════════════╝%RESET%
echo.

:: =============================================================================
:: STEP 0 — Resolve project root from script location
:: =============================================================================
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo %YELLOW%[0/6]%RESET% Project root : %PROJECT_DIR%
cd /d "%PROJECT_DIR%"

:: =============================================================================
:: STEP 1 — Verify Python 3.11+
:: =============================================================================
echo.
echo %YELLOW%[1/6]%RESET% Checking Python...

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%[ERROR]%RESET% Python not found. Install Python 3.11+ and add it to PATH.
    echo         https://www.python.org/downloads/
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! lss 3 goto :py_err
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 11 goto :py_err
echo %GREEN%[OK]%RESET% Python !PY_VERSION!
goto :py_ok
:py_err
echo %RED%[ERROR]%RESET% Python 3.11+ required. Found: !PY_VERSION!
pause & exit /b 1
:py_ok

:: =============================================================================
:: STEP 2 — Virtual environment
:: =============================================================================
echo.
echo %YELLOW%[2/6]%RESET% Setting up virtual environment...

set "VENV_DIR=%PROJECT_DIR%\.venv"

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo %GREEN%[OK]%RESET% Reusing existing .venv
) else (
    echo        Creating .venv ...
    python -m venv "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo %RED%[ERROR]%RESET% Failed to create venv.
        pause & exit /b 1
    )
    echo %GREEN%[OK]%RESET% .venv created
)

call "%VENV_DIR%\Scripts\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo %RED%[ERROR]%RESET% Could not activate venv.
    pause & exit /b 1
)
echo %GREEN%[OK]%RESET% venv activated
python -m pip install --upgrade pip --quiet

:: =============================================================================
:: STEP 3 — Install Python dependencies
:: =============================================================================
echo.
echo %YELLOW%[3/6]%RESET% Installing dependencies...

if not exist "%PROJECT_DIR%\requirements.txt" (
    echo %RED%[ERROR]%RESET% requirements.txt not found.
    pause & exit /b 1
)

pip install -r "%PROJECT_DIR%\requirements.txt" --quiet
if %ERRORLEVEL% neq 0 (
    echo %RED%[ERROR]%RESET% pip install failed. Check your connection or requirements.txt.
    pause & exit /b 1
)
echo %GREEN%[OK]%RESET% All packages installed

:: =============================================================================
:: STEP 4 — Create / load .env
:: =============================================================================
echo.
echo %YELLOW%[4/6]%RESET% Configuring .env...

set "ENV_FILE=%PROJECT_DIR%\.env"

if exist "%ENV_FILE%" (
    echo %GREEN%[OK]%RESET% .env already exists — loading values.
    goto :load_env
)

:: Interactive prompts
echo.
echo %CYAN%        ┌──────────────────────────────────────────────────┐%RESET%
echo %CYAN%        │           MySQL Connection Setup                 │%RESET%
echo %CYAN%        └──────────────────────────────────────────────────┘%RESET%
echo.
set /p "DB_HOST=        DB Host       [default: localhost] : "
if "!DB_HOST!"==""    set "DB_HOST=localhost"

set /p "DB_PORT=        DB Port       [default: 3306]      : "
if "!DB_PORT!"==""    set "DB_PORT=3306"

set /p "DB_NAME=        DB Name       [default: catalog_db] : "
if "!DB_NAME!"==""    set "DB_NAME=catalog_db"

set /p "DB_USER=        DB User       [default: root]       : "
if "!DB_USER!"==""    set "DB_USER=root"

echo        %YELLOW%Note:%RESET% password is visible while typing.
set /p "DB_PASS=        DB Password    [optional]                    : "

set /p "APP_HOST=        App Host      [default: 0.0.0.0]    : "
if "!APP_HOST!"==""   set "APP_HOST=0.0.0.0"

set "APP_PORT=8014"

set /p "APP_RELOAD=        Hot-reload?   (y/n) [default: y]    : "
if /i "!APP_RELOAD!"=="n" (set "RELOAD_FLAG=") else (set "RELOAD_FLAG=true")

:: Write .env
(
    echo # ── Catalog Service — generated by setup_and_run.bat ─────────────────────
    echo # %DATE% %TIME%
    echo.
    echo # Application
    echo PROJECT_NAME=Catalog Service
    echo API_VERSION=1.0.0
    echo API_V1_PREFIX=/api/v1
    echo.
    echo # MySQL
    echo DB_HOST=!DB_HOST!
    echo DB_PORT=!DB_PORT!
    echo DB_NAME=!DB_NAME!
    echo DB_USER=!DB_USER!
    echo DB_PASS=!DB_PASS!
    echo DATABASE_URL=mysql+aiomysql://!DB_USER!:!DB_PASS!@!DB_HOST!:!DB_PORT!/!DB_NAME!?charset=utf8mb4
    echo.
    echo # Server
    echo APP_HOST=!APP_HOST!
    echo APP_PORT=!APP_PORT!
    echo APP_RELOAD=!RELOAD_FLAG!
    echo.
    echo # Pagination
    echo DEFAULT_PAGE=1
    echo DEFAULT_LIMIT=20
    echo MAX_LIMIT=100
    echo.
    echo # CORS
    echo ALLOWED_ORIGINS=["*"]
    echo.
    echo # JWT
    echo JWT_SECRET=your-super-secret-jwt-key-change-in-production
) > "%ENV_FILE%"

echo %GREEN%[OK]%RESET% .env written.

:load_env
:: Parse .env into environment variables
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "_k=%%a"
    set "_v=%%b"
    :: Skip blank lines and comments
    if not "!_k!"=="" if not "!_k:~0,1!"=="#" (
        :: Trim leading space from value
        set "!_k!=!_v!"
    )
)

:: Fallback defaults for DB connection
if not defined DB_HOST     set "DB_HOST=localhost"
if not defined DB_PORT     set "DB_PORT=3306"
if not defined DB_NAME     set "DB_NAME=abt_dev"
if not defined DB_USER     set "DB_USER=root"
if not defined DB_PASS     set "DB_PASS=Gaurav@123"
if not defined APP_HOST    set "APP_HOST=0.0.0.0"
if not defined APP_PORT    set "APP_PORT=8014"
if not defined APP_RELOAD  set "APP_RELOAD=true"

:: =============================================================================
:: STEP 5 — MySQL: create database + apply schema
:: =============================================================================
echo.
echo %YELLOW%[5/6]%RESET% Setting up MySQL database...

:: Check mysql CLI
mysql --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %YELLOW%[WARN]%RESET% mysql client not found in PATH — skipping automatic DB setup.
    echo.
    echo        Run these commands manually:
    echo.
    echo        mysql -u %DB_USER% -p -h %DB_HOST% -P %DB_PORT% ^< catalog_service.sql
    echo.
    goto :skip_db
)

:: Build mysql auth args
set "MY_ARGS=-u %DB_USER% -h %DB_HOST% -P %DB_PORT% --protocol=TCP"
if not "%DB_PASS%"=="" set "MY_ARGS=%MY_ARGS% -p%DB_PASS%"

:: Test connection
mysql %MY_ARGS% -e "SELECT 1;" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%[ERROR]%RESET% Cannot connect to MySQL at %DB_HOST%:%DB_PORT% as %DB_USER%.
    echo        Check that MySQL is running and credentials are correct.
    pause & exit /b 1
)
echo %GREEN%[OK]%RESET% MySQL connection verified.

:: Check if DB already exists
mysql %MY_ARGS% -e "USE %DB_NAME%;" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %GREEN%[OK]%RESET% Database '%DB_NAME%' already exists.
    echo        Re-applying schema ^(safe — uses IF NOT EXISTS + INSERT IGNORE^)...
) else (
    echo        Database '%DB_NAME%' not found — creating...
    mysql %MY_ARGS% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo %RED%[ERROR]%RESET% Failed to create database '%DB_NAME%'.
        pause & exit /b 1
    )
    echo %GREEN%[OK]%RESET% Database '%DB_NAME%' created.
)

:: Apply SQL schema
if exist "%PROJECT_DIR%\catalog_service.sql" (
    echo        Applying catalog_service.sql ...
    mysql %MY_ARGS% "%DB_NAME%" < "%PROJECT_DIR%\catalog_service.sql" 2>&1
    if %ERRORLEVEL% neq 0 (
        echo %YELLOW%[WARN]%RESET% SQL script reported warnings ^(safe on re-runs — IF NOT EXISTS + INSERT IGNORE in place^).
    ) else (
        echo %GREEN%[OK]%RESET% Schema applied successfully.
    )
) else (
    echo %YELLOW%[WARN]%RESET% catalog_service.sql not found — skipping schema import.
)

:skip_db

:: =============================================================================
:: STEP 5b — Auto-fix: rename 'endpoint' folder to 'endpoints' if needed
:: =============================================================================
if exist "%PROJECT_DIR%\app\api\v1\endpoint" (
    if not exist "%PROJECT_DIR%\app\api\v1\endpoints" (
        echo %YELLOW%[FIX]%RESET%  Found 'endpoint' folder -- renaming to 'endpoints' ...
        ren "%PROJECT_DIR%\app\api\v1\endpoint" "endpoints"
        if %ERRORLEVEL% equ 0 (
            echo %GREEN%[OK]%RESET% Renamed successfully.
        ) else (
            echo %RED%[ERROR]%RESET% Rename failed. Please rename manually:
            echo         app\api\v1\endpoint  to  app\api\v1\endpoints
            pause & exit /b 1
        )
    )
)

:: =============================================================================
:: STEP 6 — Start Uvicorn
:: =============================================================================
echo.
echo %YELLOW%[6/6]%RESET% Starting Uvicorn...
echo.
echo %CYAN%%BOLD%╔══════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%%BOLD%║  Server  ^>  http://127.0.0.1:%APP_PORT%                        ║%RESET%
echo %CYAN%%BOLD%║  Docs    ^>  http://127.0.0.1:%APP_PORT%/api/v1/docs            ║%RESET%
echo %CYAN%%BOLD%║  Press Ctrl+C to stop                                    ║%RESET%
echo %CYAN%%BOLD%╚══════════════════════════════════════════════════════════╝%RESET%
echo.

set "RELOAD_ARG="
if /i "%APP_RELOAD%"=="true" set "RELOAD_ARG=--reload"

uvicorn app.main:app ^
    --host "%APP_HOST%" ^
    --port "%APP_PORT%" ^
    %RELOAD_ARG% ^
    --log-level info

if %ERRORLEVEL% neq 0 (
    echo.
    echo %RED%[ERROR]%RESET% Uvicorn exited with an error. Review the log above.
    pause & exit /b 1
)

echo.
echo %GREEN%Server stopped cleanly.%RESET%
endlocal
pause