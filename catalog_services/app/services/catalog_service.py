"""Catalog service: business logic and schema assembly."""

import json
import re
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
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


def _legacy_primary_image_url(raw_images) -> Optional[str]:
    if not raw_images:
        return None
    try:
        images = json.loads(raw_images) if isinstance(raw_images, str) else raw_images
    except (TypeError, ValueError):
        return str(raw_images)
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if isinstance(first, dict):
        return first.get("url") or first.get("src") or first.get("image_url")
    return str(first)


def _slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or fallback


def _legacy_image_payload(image_url: Optional[str]) -> list[dict]:
    return [{"url": image_url, "is_primary": True, "sort_order": 0}] if image_url else []


def _to_product_summary(product: Product) -> ProductSummarySchema:
    """Map a Product ORM instance to a ProductSummarySchema."""
    category = CategorySchema.model_validate(product.category) if product.category else None
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
        stock_quantity=int(product.stock_quantity or 0),
        is_featured=product.is_featured,
        rating_average=_f(product.rating_average),
        rating_count=product.rating_count,
        primary_image_url=_primary_image_url(product),
        category_id=product.category_id,
        category=category,
    )


def _to_product_detail(product: Product) -> ProductDetailSchema:
    """Map a Product ORM instance (with relations) to a ProductDetailSchema."""
    category = CategorySchema.model_validate(product.category) if product.category else None
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
        category=category,
        images=images,
        tags=[pt.tag for pt in product.tags],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _to_legacy_product_summary(product: dict) -> ProductSummarySchema:
    category = None
    if product.get("category__id"):
        category = CategorySchema(
            id=product.get("category__id"),
            name=product.get("category__name") or "Category",
            slug=product.get("category__slug") or "",
            description=product.get("category__description"),
            sort_order=0,
        )
    return ProductSummarySchema(
        id=product.get("id"),
        name=product.get("name") or "Product",
        slug=product.get("slug") or str(product.get("id") or ""),
        short_description=product.get("short_description"),
        price=_f(product.get("price")),
        compare_at_price=_f(product.get("compare_at_price")) if product.get("compare_at_price") else None,
        size=None,
        skin_type=None,
        availability=product.get("availability") or "in_stock",
        stock_quantity=int(product.get("stock_quantity") or product.get("stock_qty") or 0),
        is_featured=False,
        rating_average=0,
        rating_count=0,
        primary_image_url=_legacy_primary_image_url(product.get("images")),
        category_id=product.get("category_id"),
        category=category,
    )


def _to_legacy_product_detail(product: dict) -> ProductDetailSchema:
    category = None
    if product.get("category__id"):
        category = CategorySchema(
            id=product.get("category__id"),
            name=product.get("category__name") or "Category",
            slug=product.get("category__slug") or "",
            description=product.get("category__description"),
            sort_order=0,
        )
    now = datetime.utcnow()
    return ProductDetailSchema(
        id=product.get("id"),
        name=product.get("name") or "Product",
        slug=product.get("slug") or str(product.get("id") or ""),
        short_description=product.get("description"),
        long_description=product.get("description"),
        benefits=None,
        ingredients=None,
        price=_f(product.get("price")),
        compare_at_price=_f(product.get("compare_price")) if product.get("compare_price") else None,
        size=None,
        skin_type=None,
        stock_quantity=int(product.get("stock_qty") or 0),
        availability="in_stock" if int(product.get("stock_qty") or 0) > 0 else "out_of_stock",
        is_featured=False,
        rating_average=0,
        rating_count=0,
        category_id=product.get("category_id"),
        category=category,
        images=[],
        tags=[],
        created_at=product.get("created_at") or now,
        updated_at=product.get("updated_at") or now,
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
        try:
            total, products = await self._products.get_many(params)
            items = [_to_product_summary(p) for p in products]
        except (OperationalError, ProgrammingError) as exc:
            if "Unknown column" not in str(exc) and "doesn't exist" not in str(exc):
                raise
            total, legacy_products = await self._products.get_many_legacy(params)
            items = [_to_legacy_product_summary(p) for p in legacy_products]
        return ProductListResponse(
            total=total,
            page=params.page,
            limit=params.limit,
            items=items,
        )

    async def get_product(self, product_id: int | str) -> Optional[ProductDetailSchema]:
        """Return full product detail by numeric id or slug, or None if inactive."""
        product = await self._products.get_active_by_identifier(product_id)
        return _to_product_detail(product) if product else None

    async def get_related_products(
        self, product_id: int | str, limit: int = 6
    ) -> Optional[ProductListResponse]:
        """Return products related to the given product by category."""
        product = await self._products.get_active_by_identifier(product_id)
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
        if await self._uses_legacy_product_schema():
            return await self._create_legacy_admin_product(payload)

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
        if await self._uses_legacy_product_schema():
            return await self._update_legacy_admin_product(product_id, payload)

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
        if await self._uses_legacy_product_schema():
            return await self._delete_legacy_admin_product(product_id)

        product = await self._products.get_any_by_identifier(product_id)
        if not product:
            return False
        await self._products.delete_product(product)
        await self._products._session.flush()
        return True

    async def _uses_legacy_product_schema(self) -> bool:
        result = await self._products._session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'products'
                  AND COLUMN_NAME = 'stock_quantity'
                """
            )
        )
        return int(result.scalar() or 0) == 0

    async def _legacy_has_table(self, table_name: str) -> bool:
        result = await self._products._session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return int(result.scalar() or 0) > 0

    async def _legacy_category_by_slug_or_name(self, value: str) -> dict | None:
        if not await self._legacy_has_table("categories"):
            return None

        normalized = _slugify(value, "general")
        result = await self._products._session.execute(
            text(
                """
                SELECT id, name, slug, description
                FROM categories
                WHERE slug = :slug OR LOWER(name) = LOWER(:name)
                LIMIT 1
                """
            ),
            {"slug": normalized, "name": value.strip()},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def _legacy_get_or_create_category(self, name: str) -> dict:
        fallback = {
            "id": None,
            "name": name.strip(),
            "slug": _slugify(name, "general"),
            "description": None,
        }
        if not await self._legacy_has_table("categories"):
            return fallback

        existing = await self._legacy_category_by_slug_or_name(name)
        if existing:
            return existing

        try:
            await self._products._session.execute(
                text(
                    """
                    INSERT INTO categories (name, slug, description, is_active)
                    VALUES (:name, :slug, NULL, TRUE)
                    """
                ),
                {"name": fallback["name"], "slug": fallback["slug"]},
            )
            await self._products._session.flush()
        except IntegrityError:
            pass

        return await self._legacy_category_by_slug_or_name(name) or fallback

    async def _legacy_unique_product_slug(self, name: str, exclude_product_id: str | None = None) -> str:
        base_slug = _slugify(name, "product")
        slug = base_slug
        suffix = 2
        while True:
            query = "SELECT id FROM products WHERE slug = :slug"
            values = {"slug": slug}
            if exclude_product_id:
                query += " AND id != :product_id"
                values["product_id"] = exclude_product_id
            result = await self._products._session.execute(text(query + " LIMIT 1"), values)
            if not result.mappings().first():
                return slug
            slug = f"{base_slug}-{suffix}"
            suffix += 1

    async def _legacy_product_by_identifier(self, product_id: int | str) -> dict | None:
        field = "id" if not str(product_id).isdigit() else "id"
        has_categories = await self._legacy_has_table("categories")
        category_select = (
            """
                    c.id AS category__id,
                    c.name AS category__name,
                    c.slug AS category__slug,
                    c.description AS category__description
            """
            if has_categories
            else """
                    NULL AS category__id,
                    NULL AS category__name,
                    NULL AS category__slug,
                    NULL AS category__description
            """
        )
        category_join = "LEFT JOIN categories c ON c.id = p.category_id" if has_categories else ""
        result = await self._products._session.execute(
            text(
                f"""
                SELECT
                    p.id,
                    p.category_id,
                    p.name,
                    p.slug,
                    p.description,
                    p.price,
                    p.compare_price,
                    p.stock_qty,
                    p.images,
                    p.created_at,
                    p.updated_at,
                    {category_select}
                FROM products p
                {category_join}
                WHERE p.{field} = :identifier OR p.slug = :identifier
                LIMIT 1
                """
            ),
            {"identifier": str(product_id)},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def _create_legacy_admin_product(self, payload: AdminProductUpsertSchema) -> ProductDetailSchema:
        category = await self._legacy_get_or_create_category(payload.category)
        slug = await self._legacy_unique_product_slug(payload.name)
        await self._products._session.execute(
            text(
                """
                INSERT INTO products (
                    category_id, name, slug, description, price, compare_price,
                    sku, stock_qty, images, is_active
                )
                VALUES (
                    :category_id, :name, :slug, :description, :price, NULL,
                    NULL, :stock_qty, :images, TRUE
                )
                """
            ),
            {
                "category_id": category.get("id"),
                "name": payload.name.strip(),
                "slug": slug,
                "description": payload.description,
                "price": Decimal(str(payload.price)),
                "stock_qty": payload.stock,
                "images": json.dumps(_legacy_image_payload(payload.image_url)),
            },
        )
        await self._products._session.flush()
        product = await self._legacy_product_by_identifier(slug)
        return _to_legacy_product_detail(product)

    async def _update_legacy_admin_product(self, product_id: int | str, payload: AdminProductUpsertSchema) -> ProductDetailSchema | None:
        existing = await self._legacy_product_by_identifier(product_id)
        if not existing:
            return None

        category = await self._legacy_get_or_create_category(payload.category)
        slug = await self._legacy_unique_product_slug(payload.name, exclude_product_id=str(existing["id"]))
        await self._products._session.execute(
            text(
                """
                UPDATE products
                SET category_id = :category_id,
                    name = :name,
                    slug = :slug,
                    description = :description,
                    price = :price,
                    stock_qty = :stock_qty,
                    images = :images,
                    is_active = TRUE
                WHERE id = :product_id
                """
            ),
            {
                "category_id": category.get("id"),
                "name": payload.name.strip(),
                "slug": slug,
                "description": payload.description,
                "price": Decimal(str(payload.price)),
                "stock_qty": payload.stock,
                "images": json.dumps(_legacy_image_payload(payload.image_url)),
                "product_id": existing["id"],
            },
        )
        await self._products._session.flush()
        product = await self._legacy_product_by_identifier(existing["id"])
        return _to_legacy_product_detail(product)

    async def _delete_legacy_admin_product(self, product_id: int | str) -> bool:
        existing = await self._legacy_product_by_identifier(product_id)
        if not existing:
            return False
        await self._products._session.execute(
            text("UPDATE products SET is_active = FALSE WHERE id = :product_id"),
            {"product_id": existing["id"]},
        )
        await self._products._session.flush()
        return True
