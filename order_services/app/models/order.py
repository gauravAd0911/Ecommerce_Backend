from sqlalchemy import Column, DateTime, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    user_id = Column(String(100), nullable=False)
    total = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)
    payment_method = Column(String(50), nullable=False)
    shipping_address = Column(Text, nullable=False)
    item_count = Column(Integer, nullable=False)
    primary_label = Column(String(255), nullable=False)
    assigned_to_employee_id = Column(String(100), nullable=True, index=True)
    assigned_by_admin_id = Column(String(100), nullable=True)
    status_note = Column(Text, nullable=True)
    last_updated_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
