from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(settings.DB_USER)}:{quote_plus(settings.DB_PASSWORD)}"
    f"@{settings.DB_HOST}/{settings.DB_NAME}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """
    Create tables defined by SQLAlchemy models if they do not exist yet.
    """
    from app.models.notification_model import Device, Notification

    Base.metadata.create_all(bind=engine)
    _ensure_user_id_columns_are_strings()


def _ensure_user_id_columns_are_strings() -> None:
    """
    Existing local DBs may have old INT user_id columns. The frontend/auth
    services use string IDs, so keep notification ownership compatible.
    """
    with engine.begin() as connection:
        for table_name in ("devices", "notifications"):
            result = connection.execute(
                text(
                    """
                    SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = :table_name
                      AND COLUMN_NAME = 'user_id'
                    """
                ),
                {"table_name": table_name},
            ).mappings().first()

            if result and str(result["DATA_TYPE"]).lower() not in {"varchar", "char"}:
                connection.execute(text(f"ALTER TABLE {table_name} MODIFY user_id VARCHAR(128) NOT NULL"))
