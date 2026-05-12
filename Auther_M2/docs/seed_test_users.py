from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from auth.models.user import Role, User
from auth.utils.password import hash_password
from database import SessionLocal

# ⚠️ DEPRECATED: This script uses hardcoded test users for development only
# It should NOT be used in production environments
# Users should authenticate through proper signup/login flows

TEST_USERS = [
    {
        "full_name": "Alice Customer",
        "email": "alice@lumira.local",
        "phone": "+12015550101",
        "password": "Alice123!",
        "role": Role.CONSUMER,
    },
    {
        "full_name": "Bob Customer",
        "email": "bob@lumira.local",
        "phone": "+12015550102",
        "password": "Bob123!",
        "role": Role.CONSUMER,
    },
    {
        "full_name": "Carol Customer",
        "email": "carol@lumira.local",
        "phone": "+12015550103",
        "password": "Carol123!",
        "role": Role.CONSUMER,
    },
]

ADMIN_USER = {
    "full_name": "System Administrator",
    "email": "admin@lumira.local",
    "phone": None,
    "password": "Admin@123",
    "role": Role.ADMIN,
}


def create_or_update_user(db, full_name, email, phone, password, role):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"Skipped existing user: {email}")
        return existing

    user = User(
        id=str(uuid.uuid4()),
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created user: {email} (role={role.value})")
    return user


def main() -> None:
    db = SessionLocal()
    try:
        for user_data in TEST_USERS:
            create_or_update_user(
                db,
                user_data["full_name"],
                user_data["email"],
                user_data["phone"],
                user_data["password"],
                user_data["role"],
            )

        create_or_update_user(
            db,
            ADMIN_USER["full_name"],
            ADMIN_USER["email"],
            ADMIN_USER["phone"],
            ADMIN_USER["password"],
            ADMIN_USER["role"],
        )

        print("\nTest users are ready. Use the listed email/password combinations to sign in.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
