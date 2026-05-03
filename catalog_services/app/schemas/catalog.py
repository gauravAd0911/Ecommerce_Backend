"""Pydantic response schemas for the Catalog Service API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Shared base ──────────────────────────────────────────────────────────────

class _OrmBase(BaseModel):
    """Base schema with ORM mode enabled."""
    model_config = ConfigDict(from_attributes=True)


# ── Category ─────────────────────────────────────────────────────────────────

class CategorySchema(_OrmBase):
    """Lightweight category representation."""
    id:          int
    name:        str
    slug:        str
    description: Optional[str] = None
    image_url:   Optional[str] = None
    parent_id:   Optional[int] = None
    sort_order:  int


class CategoryListResponse(BaseModel):
    """Paginated list of categories."""
    total: int
    items: List[CategorySchema]


# ── Product image ─────────────────────────────────────────────────────────────

class ProductImageSchema(_OrmBase):
    """Single product media item."""
    id:         int
    url:        str
    alt_text:   Optional[str] = None
    is_primary: bool
    sort_order: int


# ── Product summary (list / card view) ────────────────────────────────────────

class ProductSummarySchema(_OrmBase):
    """Minimal product data for listing cards."""
    id:                int
    name:              str
    slug:              str
    short_description: Optional[str]   = None
    price:             float                       # float → clean JSON + clean Swagger schema
    compare_at_price:  Optional[float] = None
    size:              Optional[str]   = None
    skin_type:         Optional[str]   = None
    availability:      str
    is_featured:       bool
    rating_average:    float
    rating_count:      int
    primary_image_url: Optional[str]   = None
    category_id:       int

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={float: lambda v: round(v, 2)},
    )


# ── Product detail ────────────────────────────────────────────────────────────

class ProductDetailSchema(_OrmBase):
    """Full product data for the product detail page and cart snapshot."""
    id:                int
    name:              str
    slug:              str
    short_description: Optional[str]   = None
    long_description:  Optional[str]   = None
    benefits:          Optional[str]   = None
    ingredients:       Optional[str]   = None
    price:             float
    compare_at_price:  Optional[float] = None
    size:              Optional[str]   = None
    skin_type:         Optional[str]   = None
    stock_quantity:    int
    availability:      str
    is_featured:       bool
    rating_average:    float
    rating_count:      int
    category_id:       int
    images:            List[ProductImageSchema] = Field(default_factory=list)
    tags:              List[str]               = Field(default_factory=list)
    created_at:        datetime
    updated_at:        datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={float: lambda v: round(v, 2)},
    )


# ── Product list response ─────────────────────────────────────────────────────

class ProductListResponse(BaseModel):
    """Paginated product listing."""
    total: int
    page:  int
    limit: int
    items: List[ProductSummarySchema]


# ── Filter options ────────────────────────────────────────────────────────────

class PriceRangeSchema(BaseModel):
    """Minimum and maximum price in the live catalogue."""
    min: float
    max: float


class FilterOptionsResponse(BaseModel):
    """All available filter facets for the product listing UI."""
    categories:  List[CategorySchema]
    skin_types:  List[str]
    price_range: PriceRangeSchema
    sort_options: List[str]


# ── Home page ─────────────────────────────────────────────────────────────────

class BannerSchema(_OrmBase):
    """Hero banner for the home page carousel."""
    id:         int
    title:      str
    subtitle:   Optional[str] = None
    image_url:  str
    cta_text:   Optional[str] = None
    cta_url:    Optional[str] = None
    sort_order: int


class HomeResponse(BaseModel):
    """Composite home page payload."""
    banners:           List[BannerSchema]
    featured_products: List[ProductSummarySchema]
    top_categories:    List[CategorySchema]


class AdminProductUpsertSchema(BaseModel):
    name: str
    price: float
    stock: int = Field(ge=0)
    category: str
    description: str
    image_url: Optional[str] = Field(default=None, alias="imageUrl")
    short_description: Optional[str] = Field(default=None, alias="shortDescription")
    size: Optional[str] = None
    skin_type: Optional[str] = Field(default=None, alias="skinType")
    is_featured: bool = Field(default=False, alias="isFeatured")

    model_config = ConfigDict(populate_by_name=True)
