"""Seed demo cart data for local testing.

⚠️ DEPRECATED: This script is for development/testing purposes only.
It seeds hardcoded cart items with mock user_id=1.

This script is NOT called during application startup.
Do NOT use this in production environments.

This script supports both cart schemas:
- `carts.price`
- legacy `carts.unit_price`
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.models.cart import Cart

logger = logging.getLogger(__name__)


def _resolve_cart_price_column(db) -> str:
    candidate = db.execute(
        text(
            "SELECT COLUMN_NAME "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'carts' "
            "AND COLUMN_NAME IN ('price', 'unit_price') "
            "ORDER BY CASE COLUMN_NAME WHEN 'price' THEN 0 ELSE 1 END "
            "LIMIT 1"
        )
    ).scalar_one_or_none()
    if candidate == "price":
        return "price"
    return "unit_price"


def main() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.query(Cart).delete()
        db.commit()

        price_column = _resolve_cart_price_column(db)
        examples = [
            {"user_id": 1, "item_name": "iPhone Case", "price": Decimal("299.00"), "quantity": 1, "currency": "INR"},
            {"user_id": 1, "item_name": "Charger", "price": Decimal("199.00"), "quantity": 2, "currency": "INR"},
            {"user_id": 1, "item_name": "Earphones", "price": Decimal("99.00"), "quantity": 3, "currency": "INR"},
        ]

        insert_sql = text(
            f"INSERT INTO carts (user_id, item_name, {price_column}, currency, quantity) "
            "VALUES (:user_id, :item_name, :price, :currency, :quantity)"
        )
        for row in examples:
            db.execute(insert_sql, row)
        db.commit()

        count = db.query(Cart).filter(Cart.user_id == 1).count()
        total = db.execute(
            text(f"SELECT COALESCE(SUM({price_column} * quantity), 0) FROM carts WHERE user_id = :user_id"),
            {"user_id": 1},
        ).scalar_one()

        total_minor = int((Decimal(str(total)) * Decimal("100")).to_integral_value())
        logger.info("Seeded %s cart items for total %s (%s minor units).", count, total, total_minor)
    finally:
        db.close()


if __name__ == "__main__":
    main()
