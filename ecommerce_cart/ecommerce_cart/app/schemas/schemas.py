from datetime import datetime
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────── Product ───────────────────────────

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0, description="Price must be greater than 0")
    stock: int = Field(ge=0, description="Stock cannot be negative")
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_product_id: Optional[str] = None
    slug: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────── Cart Item ───────────────────────────

class CartItemBase(BaseModel):
    product_id: Union[int, str] = Field(..., min_length=1)
    quantity: int = Field(gt=0, description="Quantity must be at least 1")


class AddCartItemRequest(CartItemBase):
    """Request body for POST /api/cart/items"""
    product_name: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    slug: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)


class UpdateCartItemRequest(BaseModel):
    """Request body for PUT /api/cart/items/{product_id}"""
    quantity: int = Field(gt=0, description="Quantity must be at least 1")


class MergeCartRequest(BaseModel):
    guest_token: str = Field(..., min_length=1, description="Guest token used to merge the guest cart.")


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    added_at: datetime
    updated_at: datetime
    product: ProductResponse


# ─────────────────────────── Cart ───────────────────────────

class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: List[CartItemResponse] = []
    total_items: int = 0
    total_price: float = 0.0

    @classmethod
    def from_orm_with_totals(cls, cart) -> "CartResponse":
        """Build CartResponse and compute totals from ORM cart object."""
        items = [CartItemResponse.model_validate(item) for item in cart.items]
        total_items = sum(i.quantity for i in items)
        total_price = sum(i.quantity * i.product.price for i in items)

        return cls(
            id=cart.id,
            user_id=cart.user_id,
            is_active=cart.is_active,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
            items=items,
            total_items=total_items,
            total_price=round(total_price, 2),
        )


# ─────────────────────────── Generic Responses ───────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    success: bool = False


class ApiEnvelope(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[dict] = None
