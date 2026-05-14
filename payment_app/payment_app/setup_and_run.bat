@echo off
setlocal EnableExtensions DisableDelayedExpansion

cd /d "%~dp0"
set "PROJECT_ROOT=%CD%"
set "PYTHONPATH=%PROJECT_ROOT%"
set "ENV_FILE=%PROJECT_ROOT%\.env"
set "ENV_EXAMPLE=%PROJECT_ROOT%\.env.example"

echo Using PROJECT_ROOT=%PROJECT_ROOT%

rem [1/6] Virtual environment
if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" goto venv_exists

echo [1/6] Creating venv...
call :create_venv "%PROJECT_ROOT%\venv"
if errorlevel 1 goto venv_create_failed
goto after_venv

:venv_create_failed
echo Failed to create venv.
exit /b 1

:venv_exists
echo [1/6] venv already exists.

:after_venv
set "VENV_PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
set "VENV_PIP=%PROJECT_ROOT%\venv\Scripts\pip.exe"

if not exist "%VENV_PYTHON%" goto missing_venv_python
if not exist "%VENV_PIP%" goto missing_venv_pip
goto check_requirements

:missing_venv_python
echo venv python missing: %VENV_PYTHON%
exit /b 1

:missing_venv_pip
echo venv pip missing: %VENV_PIP%
exit /b 1

:check_requirements
rem [2/6] Requirements
if not exist "%PROJECT_ROOT%\requirements.txt" goto missing_requirements

echo [2/6] Installing requirements...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%VENV_PIP%" install -r "%PROJECT_ROOT%\requirements.txt"
if errorlevel 1 exit /b 1
goto setup_env

:missing_requirements
echo requirements.txt not found: %PROJECT_ROOT%\requirements.txt
exit /b 1

:setup_env
rem [3/6] Environment
if exist "%ENV_FILE%" goto env_exists
if exist "%ENV_EXAMPLE%" goto env_from_example

echo [3/6] Creating default .env...
> "%ENV_FILE%" echo MYSQL_HOST=127.0.0.1
>> "%ENV_FILE%" echo MYSQL_PORT=3306
>> "%ENV_FILE%" echo MYSQL_USER=root
>> "%ENV_FILE%" echo MYSQL_PASSWORD=Gaurav@123
>> "%ENV_FILE%" echo MYSQL_DB=auth_m2_db
>> "%ENV_FILE%" echo.
>> "%ENV_FILE%" echo RAZORPAY_KEY=replace_me
>> "%ENV_FILE%" echo RAZORPAY_SECRET=replace_me
>> "%ENV_FILE%" echo RAZORPAY_WEBHOOK_SECRET=replace_me
goto env_done

:env_from_example
echo [3/6] Creating .env from .env.example...
copy /Y "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
goto env_done

:env_exists
echo [3/6] .env already exists.

:env_done
rem SAFE .env loader
for /f "usebackq tokens=1,* delims== eol=#" %%A in ("%ENV_FILE%") do call :load_env_line "%%A" "%%B"

if not defined MYSQL_HOST set "MYSQL_HOST=127.0.0.1"
if not defined MYSQL_PORT set "MYSQL_PORT=3306"
if not defined MYSQL_USER set "MYSQL_USER=root"
if not defined MYSQL_DB set "MYSQL_DB=auth_m2_db"

rem [4/6] Create DB + apply schema
echo [4/6] Creating DB "%MYSQL_DB%" and applying schema...
where mysql >nul 2>nul
if errorlevel 1 goto mysql_missing
if defined MYSQL_PASSWORD goto mysql_with_password
goto mysql_without_password

:mysql_with_password
mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" -p%MYSQL_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS `%MYSQL_DB%`;"
if errorlevel 1 exit /b 1
mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" -p%MYSQL_PASSWORD% "%MYSQL_DB%" < "%PROJECT_ROOT%\payments_schema.sql"
if errorlevel 1 goto schema_failed
goto mysql_done

:mysql_without_password
mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" -e "CREATE DATABASE IF NOT EXISTS `%MYSQL_DB%`;"
if errorlevel 1 exit /b 1
mysql -h "%MYSQL_HOST%" -P "%MYSQL_PORT%" -u "%MYSQL_USER%" "%MYSQL_DB%" < "%PROJECT_ROOT%\payments_schema.sql"
if errorlevel 1 goto schema_failed
goto mysql_done

:mysql_missing
echo MySQL CLI not found in PATH. Skipping DB bootstrap.
goto mysql_done

:schema_failed
echo Schema apply failed.
exit /b 1

:mysql_done
rem [5/6] Seed demo cart (optional)
echo [5/6] Seeding demo cart (optional)...
if exist "%PROJECT_ROOT%\app\seed.py" "%VENV_PYTHON%" "%PROJECT_ROOT%\app\seed.py" >nul 2>nul

rem [6/6] Run server
echo [6/6] Starting server at http://127.0.0.1:8006 ...
"%VENV_PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8006
exit /b %errorlevel%

:load_env_line
if "%~1"=="" exit /b 0
set "%~1=%~2"
exit /b 0

:create_venv
set "TARGET_DIR=%~1"
if "%TARGET_DIR%"=="" exit /b 1

py -3 --version >nul 2>nul
if errorlevel 1 goto try_python
py -3 -m venv "%TARGET_DIR%"
exit /b %errorlevel%

:try_python
python --version >nul 2>nul
if errorlevel 1 goto try_python_exe
python -m venv "%TARGET_DIR%"
exit /b %errorlevel%

:try_python_exe
python.exe --version >nul 2>nul
if errorlevel 1 goto python_not_found
python.exe -m venv "%TARGET_DIR%"
exit /b %errorlevel%

:python_not_found
echo Python not found.
exit /b 1
