from sqlalchemy import Column, String, ForeignKey, Boolean, TIMESTAMP, text
from app.db.base import Base
import uuid

class Address(Base):
    __tablename__ = "addresses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(
        String(36),
        ForeignKey("app_users.id", ondelete="CASCADE"),
        nullable=False
    )

    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    landmark = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), default="India")
    address_type = Column(String(40), default="Home")

    is_default = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )
