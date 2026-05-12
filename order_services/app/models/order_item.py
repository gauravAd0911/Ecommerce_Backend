from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.dialects.mysql import BIGINT
from app.models.order import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(BIGINT(unsigned=True), ForeignKey("orders.id"))
    product_id = Column(String(100))
    product_name = Column(String(255))
    price = Column(Float)
    quantity = Column(Integer)
    image_url = Column(String(255))
