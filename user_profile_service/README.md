# User Profile Service

FastAPI microservice for managing the authenticated user's profile and saved addresses.

## Tech Stack
- FastAPI
- SQLAlchemy
- MySQL (via `pymysql`)

## Prerequisites
- Python 3.10+ including Python 3.13
- MySQL running locally

## Setup
From `C:\Advance Project\user_profile_service`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create/update `.env` (example keys already exist in the repo):
- `DATABASE_URL` (example: `mysql+pymysql://root:Root@localhost:3306/abt_dev`)
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `APP_NAME`, `DEBUG`
- `MAX_ADDRESS_LIMIT`

## Database
1. Create the database (default in `.env` is `abt_dev`).
2. Import the schema:

```powershell
mysql -u root -p abt_dev < .\user_profile_service.sql
```

Note: `setup_all.bat` currently references `sql\user_profile_service.sql`, but the SQL file in this repo is `user_profile_service.sql` in the project root.

## Run
```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8009
```

- API: `http://127.0.0.1:8009`
- Swagger UI: `http://127.0.0.1:8009/docs`

## Endpoints
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `GET /api/v1/users/me/addresses/`
- `POST /api/v1/users/me/addresses/`
- `PATCH /api/v1/users/me/addresses/{address_id}`
- `DELETE /api/v1/users/me/addresses/{address_id}`
- `PATCH /api/v1/users/me/addresses/{address_id}/default`

## Authentication (Current)
Auth is mocked right now and always uses user id `user-123` (see `app/dependencies/auth.py`). Replace this with real JWT validation when integrating with an auth service.

## Tests
Tests use `pytest` and FastAPI's `TestClient`.

```powershell
pip install pytest
pytest -q
```
