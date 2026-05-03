"""Catalog service: business logic and schema assembly."""

import re
from typing import Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ALLOWED_SORT_VALUES,
    FEATURED_PRODUCTS_LIMIT,
    HOME_BANNER_LIMIT,
)
from app.db.banner_repository import BannerRepository
from app.db.category_repository import CategoryRepository
from app.db.product_repository import ProductRepository
from app.models.catalog import Product
from app.schemas.catalog import (
    AdminProductUpsertSchema,
    BannerSchema,
    CategoryListResponse,
    CategorySchema,
    FilterOptionsResponse,
    HomeResponse,
    PriceRangeSchema,
    ProductDetailSchema,
    ProductImageSchema,
    ProductListResponse,
    ProductSummarySchema,
)
from app.schemas.filters import ProductFilterParams


def _f(value) -> float:
    """Safely cast Decimal or None to float, rounded to 2 dp."""
    return round(float(value), 2) if value is not None else 0.0


def _primary_image_url(product: Product) -> Optional[str]:
    """Return URL of the primary image, first image, or None."""
    for img in product.images:
        if img.is_primary:
            return img.url
    return product.images[0].url if product.images else None


def _to_product_summary(product: Product) -> ProductSummarySchema:
    """Map a Product ORM instance to a ProductSummarySchema."""
    return ProductSummarySchema(
        id=product.id,
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        price=_f(product.price),
        compare_at_price=_f(product.compare_at_price) if product.compare_at_price else None,
        size=product.size,
        skin_type=product.skin_type,
        availability=product.availability,
        is_featured=product.is_featured,
        rating_average=_f(product.rating_average),
        rating_count=product.rating_count,
        primary_image_url=_primary_image_url(product),
        category_id=product.category_id,
    )


def _to_product_detail(product: Product) -> ProductDetailSchema:
    """Map a Product ORM instance (with relations) to a ProductDetailSchema."""
    images = [
        ProductImageSchema(
            id=img.id,
            url=img.url,
            alt_text=img.alt_text,
            is_primary=img.is_primary,
            sort_order=img.sort_order,
        )
        for img in product.images
    ]
    return ProductDetailSchema(
        id=product.id,
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        long_description=product.long_description,
        benefits=product.benefits,
        ingredients=product.ingredients,
        price=_f(product.price),
        compare_at_price=_f(product.compare_at_price) if product.compare_at_price else None,
        size=product.size,
        skin_type=product.skin_type,
        stock_quantity=product.stock_quantity,
        availability=product.availability,
        is_featured=product.is_featured,
        rating_average=_f(product.rating_average),
        rating_count=product.rating_count,
        category_id=product.category_id,
        images=images,
        tags=[pt.tag for pt in product.tags],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


class CatalogService:
    """Orchestrates catalog repositories and assembles API response schemas."""

    def __init__(self, session: AsyncSession) -> None:
        self._products   = ProductRepository(session)
        self._categories = CategoryRepository(session)
        self._banners    = BannerRepository(session)

    async def get_home(self) -> HomeResponse:
        """Build the composite home page payload."""
        banners_orm    = await self._banners.get_active(limit=HOME_BANNER_LIMIT)
        featured_orm   = await self._products.get_featured(limit=FEATURED_PRODUCTS_LIMIT)
        top_cats_orm   = await self._categories.get_top(limit=6)

        return HomeResponse(
            banners=[BannerSchema.model_validate(b) for b in banners_orm],
            featured_products=[_to_product_summary(p) for p in featured_orm],
            top_categories=[CategorySchema.model_validate(c) for c in top_cats_orm],
        )

    async def list_products(self, params: ProductFilterParams) -> ProductListResponse:
        """Return a filtered, sorted, paginated product listing."""
        total, products = await self._products.get_many(params)
        return ProductListResponse(
            total=total,
            page=params.page,
            limit=params.limit,
            items=[_to_product_summary(p) for p in products],
        )

    async def get_product(self, product_id: int) -> Optional[ProductDetailSchema]:
        """Return full product detail, or None if not found / inactive."""
        product = await self._products.get_by_id(product_id)
        return _to_product_detail(product) if product else None

    async def get_related_products(
        self, product_id: int, limit: int = 6
    ) -> Optional[ProductListResponse]:
        """Return products related to the given product by category."""
        product = await self._products.get_by_id(product_id)
        if not product:
            return None
        related = await self._products.get_related(product, limit=limit)
        return ProductListResponse(
            total=len(related),
            page=1,
            limit=limit,
            items=[_to_product_summary(p) for p in related],
        )

    async def list_categories(self) -> CategoryListResponse:
        """Return all active categories."""
        cats  = await self._categories.get_all_active()
        items = [CategorySchema.model_validate(c) for c in cats]
        return CategoryListResponse(total=len(items), items=items)

    async def get_filter_options(self) -> FilterOptionsResponse:
        """Aggregate all available filter facets from live data."""
        categories        = await self._categories.get_all_active()
        skin_types        = await self._products.get_distinct_skin_types()
        price_min, price_max = await self._products.get_price_range()

        return FilterOptionsResponse(
            categories=[CategorySchema.model_validate(c) for c in categories],
            skin_types=skin_types,
            price_range=PriceRangeSchema(min=_f(price_min), max=_f(price_max)),
            sort_options=sorted(ALLOWED_SORT_VALUES),
        )

    async def create_admin_product(self, payload: AdminProductUpsertSchema) -> ProductDetailSchema:
        category = await self._categories.get_by_slug_or_name(payload.category)
        if not category:
            category_slug = re.sub(r"[^a-z0-9]+", "-", payload.category.strip().lower()).strip("-")
            category = await self._categories.create(name=payload.category, slug=category_slug or "general")

        slug = re.sub(r"[^a-z0-9]+", "-", payload.name.strip().lower()).strip("-")
        product = Product(
            category_id=category.id,
            name=payload.name.strip(),
            slug=slug or "product",
            short_description=(payload.short_description or payload.description)[:500],
            long_description=payload.description,
            price=Decimal(str(payload.price)),
            size=payload.size,
            skin_type=payload.skin_type,
            stock_quantity=payload.stock,
            availability="in_stock" if payload.stock > 0 else "out_of_stock",
            is_featured=payload.is_featured,
            is_active=True,
        )
        await self._products.create_product(product)
        if payload.image_url:
            await self._products.save_image(product.id, payload.image_url)
        await self._products._session.refresh(product)
        return _to_product_detail(await self._products.get_any_by_identifier(product.id))

    async def update_admin_product(self, product_id: int | str, payload: AdminProductUpsertSchema) -> ProductDetailSchema | None:
        product = await self._products.get_any_by_identifier(product_id)
        if not product:
            return None

        category = await self._categories.get_by_slug_or_name(payload.category)
        if not category:
            category_slug = re.sub(r"[^a-z0-9]+", "-", payload.category.strip().lower()).strip("-")
            category = await self._categories.create(name=payload.category, slug=category_slug or "general")

        product.category_id = category.id
        product.name = payload.name.strip()
        product.short_description = (payload.short_description or payload.description)[:500]
        product.long_description = payload.description
        product.price = Decimal(str(payload.price))
        product.stock_quantity = payload.stock
        product.availability = "in_stock" if payload.stock > 0 else "out_of_stock"
        product.is_featured = payload.is_featured
        product.size = payload.size
        product.skin_type = payload.skin_type
        product.slug = re.sub(r"[^a-z0-9]+", "-", payload.name.strip().lower()).strip("-") or product.slug

        if payload.image_url:
            if product.images:
                product.images[0].url = payload.image_url
                product.images[0].is_primary = True
            else:
                await self._products.save_image(product.id, payload.image_url)

        await self._products._session.flush()
        return _to_product_detail(await self._products.get_any_by_identifier(product.id))

    async def delete_admin_product(self, product_id: int | str) -> bool:
        product = await self._products.get_any_by_identifier(product_id)
        if not product:
            return False
        await self._products.delete_product(product)
        await self._products._session.flush()
        return True
