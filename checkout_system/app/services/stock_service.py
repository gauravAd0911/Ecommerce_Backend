"""
Stock management service for checkout system (MVP).
Deducts stock when guest orders are completed.
Skips reservation system if disabled.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def deduct_stock_for_guest_order(db: Session, order_items: list) -> bool:
    """
    Deduct stock for a completed guest order.
    
    Args:
        db: Database session
        order_items: List of items in order, each with product_id and quantity
        
    Returns:
        bool: True if deduction successful, False otherwise
    """
    
    cfg = get_settings()
    
    if not cfg.deduct_stock_on_order:
        logger.info("Stock deduction disabled. Skipping...")
        return True
    
    try:
        from app.models.models import Product
        
        for item in order_items:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 1)
            
            # Find product by external_product_id or id
            product = db.query(Product).filter(
                (Product.id == product_id) | 
                (Product.external_product_id == str(product_id))
            ).first()
            
            if not product:
                logger.warning(f"Product {product_id} not found. Skipping deduction.")
                continue
            
            old_stock = product.stock_qty if hasattr(product, 'stock_qty') else getattr(product, 'stock', 0)
            
            # Deduct stock
            if hasattr(product, 'stock_qty'):
                product.stock_qty = max(0, old_stock - quantity)
            elif hasattr(product, 'stock'):
                product.stock = max(0, old_stock - quantity)
            
            logger.info(
                f"Stock deducted: Product {product_id} "
                f"{old_stock} → {old_stock - quantity} "
                f"(qty: {quantity})"
            )
        
        db.commit()
        logger.info("Stock deduction completed for guest order")
        return True
        
    except Exception as e:
        logger.error(f"Stock deduction failed: {e}")
        db.rollback()
        return False


def is_reservation_enabled() -> bool:
    """Check if reservation system is enabled."""
    cfg = get_settings()
    return cfg.enable_stock_reservation
