@echo off
echo =========================================
echo ECOMMERCE CART SERVICE — AUTO SETUP
echo Running on port 8003
echo =========================================

REM 1. Create Virtual Environment
if not exist venv (
    echo ðŸ“¦ Creating virtual environment...
    python -m venv venv
)

REM 2. Activate venv
call venv\Scripts\activate

REM 3. Install Requirements
echo ðŸ“¦ Installing dependencies...
pip install -r requirements.txt

REM 4. Run SQL Script
echo ðŸ›  Running SQL setup...
mysql -u root -pGaurav@123 < ecommerce_cart_full.sql

REM 5. Start FastAPI Server
echo Starting FastAPI server on port 8003...
uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload

pause
