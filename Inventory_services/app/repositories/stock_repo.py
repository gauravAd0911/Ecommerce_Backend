from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.stock import Stock


class StockRepository:
    """
    Handles stock database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_stock_for_update(self, product_id: int, warehouse_id: int) -> Stock | None:
        """
        Fetch stock row with FOR UPDATE lock.

        Prevents concurrent overselling.
        """
        stmt = (
            select(Stock)
            .where(
                Stock.product_id == product_id,
                Stock.warehouse_id == warehouse_id
            )
            .with_for_update()
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_stock(self, product_id: int, warehouse_id: int) -> Stock | None:
        """
        Fetch stock without lock.
        """
        stmt = select(Stock).where(
            Stock.product_id == product_id,
            Stock.warehouse_id == warehouse_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create_stock(
        self,
        product_id: int,
        warehouse_id: int,
        total_quantity: int = 0,
        reserved_quantity: int = 0,
    ) -> Stock:
        stock = Stock(
            product_id=product_id,
            warehouse_id=warehouse_id,
            total_quantity=total_quantity,
            reserved_quantity=reserved_quantity,
        )
        self.db.add(stock)
        self.db.flush()
        return stock