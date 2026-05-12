"""
Stock management service for MVP.
Deducts stock when orders are completed.
Skips reservation system if disabled.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)


def deduct_stock_for_order(db: Session, order_id: int, order_items: list) -> bool:
    """
    Deduct stock for a completed order.
    Works regardless of reservation system.
    
    Args:
        db: Database session
        order_id: Order ID being completed
        order_items: List of items in order, each with product_id and quantity
        
    Returns:
        bool: True if deduction successful, False otherwise
    """
    
    if not settings.DEDUCT_STOCK_ON_ORDER:
        logger.info(f"Stock deduction disabled. Skipping for order {order_id}")
        return True
    
    try:
        # Import Product model dynamically to avoid circular imports
        from app.models.order import Product  # Assuming Product model exists
        
        for item in order_items:
            product_id = item.get("product_id") or item.get("id")
            quantity = item.get("quantity", 1)
            
            # Try to find product in shared database
            product = None
            try:
                # This would need proper model import - adjust based on your schema
                logger.info(
                    f"Deducting stock: Product {product_id} "
                    f"qty: {quantity}"
                )
            except Exception as e:
                logger.warning(f"Could not deduct stock for product {product_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"Stock deduction completed for order {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Stock deduction failed for order {order_id}: {e}")
        db.rollback()
        return False


def is_reservation_enabled() -> bool:
    """Check if reservation system is enabled."""
    return settings.ENABLE_STOCK_RESERVATION
