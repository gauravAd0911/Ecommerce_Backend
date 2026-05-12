"""Product API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Product
from app.schemas.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/api/products", tags=["Products"])


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

ERROR_PRODUCT_NOT_FOUND = "Product not found."

DbSession = Annotated[Session, Depends(get_db)]
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
ProductId = Annotated[int, Path(ge=1)]


@router.get("", summary="List all active products")
def list_products(
    skip: Skip = 0,
    limit: Limit = DEFAULT_PAGE_SIZE,
    *,
    db: DbSession,
) -> list[ProductResponse]:
    products = (
        db.query(Product)
        .filter(Product.is_active.is_(True))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [ProductResponse.model_validate(product) for product in products]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new product")
def create_product(payload: ProductCreate, *, db: DbSession) -> ProductResponse:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductResponse.model_validate(product)


@router.get("/{product_id}", summary="Get product by id")
def get_product(product_id: ProductId, *, db: DbSession) -> ProductResponse:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_PRODUCT_NOT_FOUND)
    return ProductResponse.model_validate(product)
