from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.models.address import Address


def create(db: Session, data: dict):
    try:
        if data.get("is_default"):
            db.query(Address).filter(Address.user_id == data["user_id"]).update({"is_default": False})

        address = Address(**data)
        db.add(address)
        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError:
        db.rollback()
        raise


def get_by_user(db: Session, user_id: str):
    return (
        db.query(Address)
        .filter(Address.user_id == user_id)
        .order_by(Address.is_default.desc())
        .all()
    )


def count_by_user(db: Session, user_id: str):
    return db.query(Address).filter(Address.user_id == user_id).count()


def count_default_by_user(db: Session, user_id: str):
    return db.query(Address).filter(Address.user_id == user_id, Address.is_default.is_(True)).count()


def get_by_id(db: Session, address_id: str):
    return db.query(Address).filter(Address.id == address_id).first()


def update(db: Session, address: Address, data: dict):
    try:
        if data.get("is_default") is True:
            db.query(Address).filter(Address.user_id == address.user_id).update({"is_default": False})

        for key, value in data.items():
            setattr(address, key, value)

        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError:
        db.rollback()
        raise


def delete(db: Session, address: Address):
    try:
        user_id = address.user_id
        address_id = address.id
        was_default = address.is_default
        db.delete(address)
        if was_default:
            replacement = db.query(Address).filter(Address.user_id == user_id, Address.id != address_id).first()
            if replacement:
                replacement.is_default = True
        db.commit()
        return {"message": "Deleted successfully"}
    except SQLAlchemyError:
        db.rollback()
        raise


def set_default(db: Session, user_id: str, address_id: str):
    try:
        address = db.query(Address).filter(
            Address.id == address_id,
            Address.user_id == user_id,
        ).first()
        if not address:
            raise ValueError("Address not found")

        db.query(Address).filter(Address.user_id == user_id).update({"is_default": False})

        address.is_default = True

        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError:
        db.rollback()
        raise
