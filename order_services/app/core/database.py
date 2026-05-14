import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)
DATABASE_URL = settings.DB_URL or "mysql+pymysql://root:Gaurav%40123@localhost/abt_dev"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Create missing tables for the configured database.
    """
    from app.models.order import Base
    from app.models import order_item, tracking  # noqa: F401

    logger.info("Initializing order service database schema")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    _repair_order_schema()
    _repair_order_items_schema()
    logger.info("Order service database schema initialization completed")


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _repair_order_items_schema() -> None:
    """Repair the order_items schema for the current OrderItem ORM."""
    inspector = inspect(engine)
    if "order_items" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        try:
            connection.execute(text("ALTER TABLE order_items MODIFY COLUMN product_id VARCHAR(100) NULL"))
        except OperationalError as exc:
            if "Incorrect column specifier" not in str(exc) and "Duplicate column name" not in str(exc):
                raise


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}
    return index_name in indexes or index_name in unique_constraints


def _repair_order_schema() -> None:
    """Add columns expected by the current Order ORM to existing local DBs.

    The original setup script used CREATE TABLE IF NOT EXISTS, which does not
    evolve tables already created with the older payment-oriented schema.
    """
    inspector = inspect(engine)
    if "orders" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    column_definitions = {
        "guest_token": "VARCHAR(255) NULL",
        "guest_email": "VARCHAR(255) NULL",
        "guest_phone": "VARCHAR(30) NULL",
        "total": "DECIMAL(10,2) NULL",
        "subtotal": "DECIMAL(10,2) NULL",
        "shipping_amount": "DECIMAL(10,2) NULL",
        "discount_amount": "DECIMAL(10,2) NULL",
        "tax_amount": "DECIMAL(10,2) NULL",
        "payment_method": "VARCHAR(50) NULL",
        "shipping_address": "TEXT NULL",
        "item_count": "INT NULL",
        "primary_label": "VARCHAR(255) NULL",
        "assigned_to_employee_id": "VARCHAR(100) NULL",
        "assigned_by_admin_id": "VARCHAR(100) NULL",
        "status_note": "TEXT NULL",
        "last_updated_by": "VARCHAR(100) NULL",
        "updated_at": "DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, definition in column_definitions.items():
            if column_name not in existing_columns:
                try:
                    connection.execute(text(f"ALTER TABLE orders ADD COLUMN {column_name} {definition}"))
                    existing_columns.add(column_name)
                except OperationalError as exc:
                    if "Duplicate column name" not in str(exc):
                        raise

        total_expression = (
            "COALESCE(total, total_amount_minor / 100)"
            if "total_amount_minor" in existing_columns
            else "COALESCE(total, 0)"
        )
        connection.execute(
            text(
                f"""
                UPDATE orders
                SET
                    total = {total_expression},
                    payment_method = COALESCE(payment_method, 'razorpay'),
                    shipping_address = COALESCE(shipping_address, ''),
                    item_count = COALESCE(item_count, 0),
                    primary_label = COALESCE(primary_label, order_number),
                    status = CASE
                        WHEN LOWER(status) = 'paid' THEN 'CONFIRMED'
                        WHEN LOWER(status) = 'pending' THEN 'PLACED'
                        WHEN LOWER(status) = 'failed' THEN 'PAYMENT_FAILED'
                        WHEN LOWER(status) = 'cancelled' THEN 'CANCELLED'
                        ELSE status
                    END
                WHERE total IS NULL
                   OR payment_method IS NULL
                   OR shipping_address IS NULL
                   OR item_count IS NULL
                   OR primary_label IS NULL
                   OR LOWER(status) IN ('paid', 'pending', 'failed', 'cancelled')
                """
            )
        )

        refreshed = inspect(connection)
        index_definitions = {
            "idx_orders_guest_token": "CREATE INDEX idx_orders_guest_token ON orders (guest_token)",
            "idx_orders_guest_email": "CREATE INDEX idx_orders_guest_email ON orders (guest_email)",
            "idx_orders_assigned_to_employee_id": "CREATE INDEX idx_orders_assigned_to_employee_id ON orders (assigned_to_employee_id)",
        }
        for index_name, statement in index_definitions.items():
            if not _index_exists(refreshed, "orders", index_name):
                try:
                    connection.execute(text(statement))
                except OperationalError as exc:
                    if "Duplicate" not in str(exc):
                        raise
