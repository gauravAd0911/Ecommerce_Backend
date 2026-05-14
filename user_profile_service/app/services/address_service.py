from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.constants import MAX_ADDRESS_LIMIT
from app.db.models.user import User
from app.repositories import address_repository
from app.utils.exceptions import AddressLimitExceededException

ADDRESS_NOT_FOUND = "Address not found"


def create_address(db: Session, user_id: str, data: dict):
    """Create a user address, creating the local profile user if needed."""
    try:
        existing_count = address_repository.count_by_user(db, user_id)
        if existing_count >= MAX_ADDRESS_LIMIT:
            raise AddressLimitExceededException(MAX_ADDRESS_LIMIT)

        if existing_count == 0:
            data["is_default"] = True
        elif address_repository.count_default_by_user(db, user_id) == 0:
            data.setdefault("is_default", True)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                id=user_id,
                email=data.pop("user_email", None) or f"{user_id}@profile.local",
                full_name=data.get("full_name") or "Customer",
                phone=data.get("phone"),
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.full_name = data.get("full_name") or user.full_name
            user.phone = data.get("phone") or user.phone

        data["user_id"] = user_id
        return address_repository.create(db, data)
    except SQLAlchemyError:
        db.rollback()
        raise


def get_addresses(db: Session, user_id: str):
    """Get all addresses for user."""
    return address_repository.get_by_user(db, user_id)


def get_address(db: Session, user_id: str, address_id: str):
    """Get one address owned by the current user."""
    address = address_repository.get_by_id(db, address_id)

    if not address or address.user_id != user_id:
        raise ValueError(ADDRESS_NOT_FOUND)

    return address


def update_address(db: Session, user_id: str, address_id: str, data: dict):
    """Update address."""
    address = address_repository.get_by_id(db, address_id)

    if not address or address.user_id != user_id:
        raise ValueError(ADDRESS_NOT_FOUND)

    return address_repository.update(db, address, data)


def delete_address(db: Session, user_id: str, address_id: str):
    """Delete address."""
    address = address_repository.get_by_id(db, address_id)

    if not address or address.user_id != user_id:
        raise ValueError(ADDRESS_NOT_FOUND)

    return address_repository.delete(db, address)


def set_default_address(db: Session, user_id: str, address_id: str):
    """Set default address."""
    return address_repository.set_default(db, user_id, address_id)
