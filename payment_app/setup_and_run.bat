@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"
set "PYTHONPATH=%PROJECT_ROOT%"

echo Using PROJECT_ROOT=%PROJECT_ROOT%

rem [1/6] Virtual environment
if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
  echo [1/6] venv already exists.
) else (
  echo [1/6] Creating venv...
  call :create_venv "%PROJECT_ROOT%\venv"
  if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
  )
)

set "VENV_PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
set "VENV_PIP=%PROJECT_ROOT%\venv\Scripts\pip.exe"
if not exist "%VENV_PYTHON%" (
  echo venv python missing: %VENV_PYTHON%
  exit /b 1
)
if not exist "%VENV_PIP%" (
  echo venv pip missing: %VENV_PIP%
  exit /b 1
)

rem [2/6] Requirements
if not exist "%PROJECT_ROOT%\requirements.txt" (
  echo requirements.txt not found: %PROJECT_ROOT%\requirements.txt
  exit /b 1
)

echo [2/6] Installing requirements...
"%VENV_PYTHON%" -m pip install --upgrade pip "setuptools==81.0.0"
if errorlevel 1 exit /b 1
"%VENV_PIP%" install -r "%PROJECT_ROOT%\requirements.txt"
if errorlevel 1 exit /b 1

rem [3/6] Environment
if exist "%PROJECT_ROOT%\.env" (
  echo [3/6] .env already exists.
) else if exist "%PROJECT_ROOT%\.env.example" (
  echo [3/6] Creating .env from .env.example...
  copy /Y "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env" >nul
  if errorlevel 1 exit /b 1
) else (
  echo [3/6] Creating default .env...
  (
    echo MYSQL_HOST=127.0.0.1
    echo MYSQL_PORT=3306
    echo MYSQL_USER=root
    echo MYSQL_PASSWORD=Gaurav@123
    echo MYSQL_DB=abt_dev
    echo.
    echo RAZORPAY_KEY=replace_me
    echo RAZORPAY_SECRET=replace_me
    echo RAZORPAY_WEBHOOK_SECRET=replace_me
  ) > "%PROJECT_ROOT%\.env"
  if errorlevel 1 exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in ("%PROJECT_ROOT%\.env") do (
  set "k=%%A"
  if defined k (
    if not "!k:~0,1!"=="#" (
      set "%%A=%%B"
    )
  )
)

if not defined MYSQL_HOST set "MYSQL_HOST=127.0.0.1"
if not defined MYSQL_PORT set "MYSQL_PORT=3306"
if not defined MYSQL_USER set "MYSQL_USER=root"
if not defined MYSQL_DB set "MYSQL_DB=abt_dev"

rem [4/6] Create DB + apply schema
echo [4/6] Creating DB "%MYSQL_DB%" and applying schema...
where mysql >nul 2>nul
if errorlevel 1 (
  echo MySQL CLI not found in PATH. Skipping DB bootstrap.
) else (
  if defined MYSQL_PASSWORD (
    mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" -p%MYSQL_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS `%MYSQL_DB%` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    if errorlevel 1 exit /b 1
    mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" -p%MYSQL_PASSWORD% "%MYSQL_DB%" < "%PROJECT_ROOT%\payments_schema.sql"
  ) else (
    mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" -e "CREATE DATABASE IF NOT EXISTS `%MYSQL_DB%` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    if errorlevel 1 exit /b 1
    mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" "%MYSQL_DB%" < "%PROJECT_ROOT%\payments_schema.sql"
  )
  if errorlevel 1 (
    echo Schema apply failed. Check MySQL service and credentials in .env
    exit /b 1
  )
)

rem [5/6] Seed demo cart (optional)
echo [5/6] Seeding demo cart (optional)...
if exist "%PROJECT_ROOT%\app\seed.py" (
  "%VENV_PYTHON%" "%PROJECT_ROOT%\app\seed.py" >nul 2>nul
)

rem [6/6] Run server
echo [6/6] Starting server at http://127.0.0.1:8006 ...
"%VENV_PYTHON%" -m uvicorn app.main:app --reload --app-dir "%PROJECT_ROOT%" --port 8006
exit /b %errorlevel%

:create_venv
set "TARGET_DIR=%~1"
if "%TARGET_DIR%"=="" exit /b 1

rem Prefer Python launcher if available
py -3 --version >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv "%TARGET_DIR%"
  exit /b %errorlevel%
)

rem Fallback to python on PATH
python --version >nul 2>nul
if not errorlevel 1 (
  python -m venv "%TARGET_DIR%"
  exit /b %errorlevel%
)

python.exe --version >nul 2>nul
if not errorlevel 1 (
  python.exe -m venv "%TARGET_DIR%"
  exit /b %errorlevel%
)

echo Python was not found.
echo Install Python 3.11+ (or enable the `py` launcher) and try again.
exit /b 1
