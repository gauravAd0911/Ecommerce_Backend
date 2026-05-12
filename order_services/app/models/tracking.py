from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.mysql import BIGINT
from app.models.order import Base


class Tracking(Base):
    __tablename__ = "order_tracking"

    id = Column(Integer, primary_key=True)
    order_id = Column(BIGINT(unsigned=True), ForeignKey("orders.id"))
    status = Column(String(50))
    message = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())