from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.order_item import OrderItem


class OrderRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_order(self, **kwargs):
        order = Order(**kwargs)
        self.db.add(order)
        self.db.flush()  # Ensure ID is generated
        
        # Verify order was created with required fields
        if not order.id:
            raise ValueError("Order ID was not generated after flush. Database error.")
        if not order.order_number:
            raise ValueError("Order number was not set. Database error.")
        
        return order

    def add_items(self, order_id, items):
        for item in items:
            db_item = OrderItem(
                order_id=order_id,
                product_id=self._item_value(item, "product_id", "productId"),
                product_name=self._item_value(item, "product_name", "productName"),
                price=self._item_value(item, "price"),
                quantity=self._item_value(item, "quantity"),
                image_url=self._item_value(item, "image_url", "imageUrl")
            )
            self.db.add(db_item)

    def get_all_orders(self):
        return self.db.query(Order).order_by(Order.created_at.desc()).all()

    def get_orders_for_user(self, user_id, email=None):
        query = self.db.query(Order).filter(Order.user_id == user_id)
        normalized_email = str(email or "").lower().strip()
        if normalized_email:
            query = self.db.query(Order).filter(
                (Order.user_id == user_id) | (Order.guest_email == normalized_email)
            )
        return query.order_by(Order.created_at.desc()).all()

    def get_guest_orders_by_email(self, email, order_number=None, limit=20):
        query = self.db.query(Order).filter(Order.guest_email == str(email or "").lower().strip())
        if order_number:
            query = query.filter(Order.order_number == str(order_number).strip())
        return query.order_by(Order.created_at.desc()).limit(limit).all()

    def get_order(self, order_id):
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_order_by_number(self, order_number):
        result = self.db.query(Order).filter(Order.order_number == order_number).first()
        if result:
            self.db.refresh(result)
        return result

    def get_order_by_payment_reference(self, payment_reference):
        return self.db.query(Order).filter(Order.payment_reference == payment_reference).first()

    def get_order_for_user(self, order_id, user_id, email=None):
        normalized_email = str(email or "").lower().strip()
        query = self.db.query(Order).filter(
            (Order.user_id == user_id) | (Order.guest_email == normalized_email)
            if normalized_email
            else (Order.user_id == user_id)
        )
        if str(order_id).isdigit():
            query = query.filter(Order.id == int(order_id))
        else:
            query = query.filter(Order.order_number == str(order_id))
        result = query.first()
        if result:
            self.db.refresh(result)
        return result

    def get_items_for_order(self, order_id):
        return self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    def update_status(self, order_id, status):
        order = self.get_order(order_id)
        if not order:
            return None

        order.status = status
        self.db.commit()
        self.db.refresh(order)
        return order

    def assign_order(self, order_id, employee_id, assigned_by):
        order = self.get_order(order_id)
        if not order:
            return None

        order.assigned_to_employee_id = employee_id
        order.assigned_by_admin_id = assigned_by
        self.db.commit()
        self.db.refresh(order)
        return order

    @staticmethod
    def _item_value(item, *keys):
        if isinstance(item, dict):
            for key in keys:
                if key in item:
                    return item[key]
            return None

        for key in keys:
            if hasattr(item, key):
                return getattr(item, key)
        return None
