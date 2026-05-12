# Review Services

FastAPI backend for product reviews with verified-purchaser checks, rating summaries, and a transactional outbox for review events.

## Structure

```text
review_services/
|-- app/
|   |-- api/v1/endpoints/   # FastAPI routes
|   |-- core/               # config, auth, constants, exceptions
|   |-- db/                 # async SQLAlchemy session factory
|   |-- events/             # outbox event publisher
|   |-- models/             # ORM models
|   |-- repositories/       # database query layer
|   |-- schemas/            # Pydantic request/response models
|   `-- services/           # business logic and outbox relay worker
|-- requirements.txt
|-- schema.sql
|-- setup.bat
`-- sonar-project.properties
```

## Features

- List published reviews for a product with pagination
- Aggregate product rating summary
- Create reviews only for verified purchasers
- Prevent duplicate reviews per user/product
- Patch a review only when owned by the current user
- Write domain events to `outbox_events`
- Relay pending outbox events in the background

## Run Locally

1. Create or activate a Python 3.11 environment.
2. Install dependencies:

```bat
pip install -r requirements.txt
```

3. Update `.env` with MySQL credentials and JWT settings.
   `JWT_SECRET` and `JWT_ALGORITHM` must exactly match the auth service
   (`Auther_M2/Auther_M/.env`) because review endpoints validate tokens issued
   by that service.
4. Apply `schema.sql` to the target MySQL database.
5. Start the app:

```bat
uvicorn app.main:app --reload
```

Swagger UI is available at `http://127.0.0.1:8000/docs`.

## Key Environment Variables

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `DEFAULT_PAGE_SIZE`
- `MAX_PAGE_SIZE`

## SonarQube

This project can be scanned with SonarQube Community Edition or a free SonarCloud project.

Run a scan with:

```bat
sonar-scanner
```

The included configuration focuses on the application code under `app/` and excludes `venv/`.
