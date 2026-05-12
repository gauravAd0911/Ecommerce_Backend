from typing import Dict, Any
from sqlalchemy.orm import Session
from app.repositories.order_repo import OrderRepository
from app.repositories.tracking_repo import TrackingRepository
from app.core.constants import OrderStatus
from app.services.notification_service import NotificationService
from app.services.stock_service import deduct_stock_for_order
from app.core.config import settings
import uuid


class OrderService:
    """
    Handles order business logic.
    """

    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.tracking_repo = TrackingRepository(db)
        self.notification = NotificationService()

    def finalize_order(self, *, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Finalize order after validation and payment.

        Args:
            data (dict): Order payload
            user_id (int): User placing the order

        Returns:
            dict: Created order response
        """

        self._validate_order_data(data)

        try:
            order_number = self._generate_order_number()

            order = self.order_repo.create_order(
                user_id=user_id,
                order_number=order_number,
                guest_token=data.get("guest_token"),
                guest_email=data.get("guest_email"),
                guest_phone=data.get("guest_phone"),
                payment_reference=data.get("payment_reference"),
                total=data["total"],
                payment_method=data["payment_method"],
                shipping_address=data["shipping_address"],
                item_count=data["item_count"],
                primary_label=data["primary_label"],
                status=OrderStatus.PLACED
            )

            self.order_repo.add_items(order.id, data["items"])

            self.tracking_repo.add_tracking(
                order.id,
                OrderStatus.PLACED,
                "Order placed successfully"
            )
            
            # MVP: Deduct stock after order creation
            if settings.DEDUCT_STOCK_ON_ORDER:
                deduct_stock_for_order(self.db, order.id, data.get("items", []))
            
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "orderNumber": order_number,
            "status": OrderStatus.PLACED
        }

    def mark_delivered(self, order_id: int, phone: str) -> None:
        """
        Mark order as delivered and send notification.
        """

        self.order_repo.update_status(order_id, OrderStatus.DELIVERED)

        self.tracking_repo.add_tracking(
            order_id,
            OrderStatus.DELIVERED,
            "Delivered successfully"
        )

        # Send SMS notification
        self.notification.send_delivery_sms(phone)

    # =========================
    # PRIVATE HELPERS
    # =========================

    def _generate_order_number(self) -> str:
        """
        Generate unique order number.
        """
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    def _validate_order_data(self, data: Dict[str, Any]) -> None:
        """
        Validate incoming order data.

        Raises:
            ValueError: If required fields are missing
        """

        required_fields = [
            "total",
            "payment_method",
            "shipping_address",
            "item_count",
            "primary_label"
        ]

        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        items = data.get("items") or []
        if not items:
            raise ValueError("Order must contain at least one item")

        calculated_item_count = sum(self._item_value(item, "quantity") or 0 for item in items)
        if calculated_item_count != data["item_count"]:
            raise ValueError("Item count does not match order items")

        subtotal = sum(
            (self._item_value(item, "price") or 0) * (self._item_value(item, "quantity") or 0)
            for item in items
        )
        shipping_amount = float(data.get("shipping_amount") or 0)
        discount_amount = float(data.get("discount_amount") or 0)
        tax_amount = float(data.get("tax_amount") or 0)

        expected_total = subtotal + shipping_amount + tax_amount - discount_amount
        if round(float(expected_total), 2) != round(float(data["total"]), 2):
            raise ValueError("Order total does not match order items")

    @staticmethod
    def _item_value(item, key: str):
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)
