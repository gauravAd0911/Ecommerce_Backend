from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from auth.models.user import Role, User
from auth.utils.password import hash_password
from database import SessionLocal

# ⚠️ DEPRECATED: This script uses hardcoded admin credentials for development only
# It should NOT be used in production environments
# Admin users should be created through proper administrative signup flows

ADMIN_EMAIL = "admin@lumira.local"
ADMIN_PASSWORD = "Admin@123"


def create_admin_user() -> None:
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == Role.ADMIN).first()
        if existing_admin:
            print("Admin user already exists:")
            print(f"  id: {existing_admin.id}")
            print(f"  email: {existing_admin.email}")
            return

        admin = User(
            id=str(uuid.uuid4()),
            full_name="System Administrator",
            email=ADMIN_EMAIL,
            phone=None,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=Role.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        db.commit()
        print("Created admin user successfully:")
        print(f"  email: {ADMIN_EMAIL}")
        print(f"  password: {ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
