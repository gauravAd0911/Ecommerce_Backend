import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"mysql+pymysql://{quote_plus(os.getenv('DB_USER') or '')}:{quote_plus(os.getenv('DB_PASSWORD') or '')}"
    f"@{os.getenv('DB_HOST') or 'localhost'}:{os.getenv('DB_PORT') or '3306'}/{os.getenv('DB_NAME') or ''}"
)

engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
