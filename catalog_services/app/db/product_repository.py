"""Product repository: encapsulates all database access for products."""

from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    SORT_NEWEST,
    SORT_POPULAR,
    SORT_PRICE_ASC,
    SORT_PRICE_DESC,
    SORT_RATING_DESC,
)
from app.models.catalog import Product, ProductImage
from app.schemas.filters import ProductFilterParams

_SORT_MAP = {
    SORT_PRICE_ASC: Product.price.asc(),
    SORT_PRICE_DESC: Product.price.desc(),
    SORT_RATING_DESC: Product.rating_average.desc(),
    SORT_NEWEST: Product.created_at.desc(),
    SORT_POPULAR: Product.rating_count.desc(),
}


class ProductRepository:
    """Data-access layer for Product entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_products_query(self) -> Select:
        """Return a base SELECT limited to active products."""
        return select(Product).where(Product.is_active.is_(True))

    def _apply_filters(self, query: Select, params: ProductFilterParams) -> Select:
        """Apply all user-supplied filter predicates to an existing query."""
        if params.q:
            term = f"%{params.q}%"
            query = query.where(
                or_(
                    Product.name.ilike(term),
                    Product.short_description.ilike(term),
                )
            )
        if params.category:
            query = query.join(Product.category).where(
                Product.category.has(slug=params.category)
            )
        if params.price_min is not None:
            query = query.where(Product.price >= Decimal(str(params.price_min)))
        if params.price_max is not None:
            query = query.where(Product.price <= Decimal(str(params.price_max)))
        if params.skin_type:
            query = query.where(Product.skin_type == params.skin_type)
        return query

    def _apply_sort(self, query: Select, sort: Optional[str]) -> Select:
        """Apply order-by clause using the validated sort key."""
        order_clause = _SORT_MAP.get(sort or "", Product.created_at.desc())
        return query.order_by(order_clause)

    async def get_many(
        self, params: ProductFilterParams
    ) -> Tuple[int, list[Product]]:
        """Return (total_count, page_of_products) with filters applied."""
        base = self._active_products_query()
        base = self._apply_filters(base, params)

        count_query = select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_query)).scalar_one()

        items_query = (
            self._apply_sort(base, params.sort)
            .offset((params.page - 1) * params.limit)
            .limit(params.limit)
            .options(selectinload(Product.images), selectinload(Product.category))
        )
        result = await self._session.execute(items_query)
        return total, list(result.scalars().all())

    async def get_many_legacy(self, params: ProductFilterParams) -> Tuple[int, list[dict]]:
        """Return products from the legacy UUID/JSON catalog table shape.

        Some local databases were created before catalog_service.sql was
        updated. They have description/compare_price/stock_qty/images columns
        instead of the newer normalized product schema. This read path keeps the
        storefront alive without destructive table rebuilds.
        """
        filters = ["p.is_active = 1"]
        values: dict[str, object] = {
            "limit": params.limit,
            "offset": (params.page - 1) * params.limit,
        }

        if params.q:
            filters.append("(p.name LIKE :q OR p.description LIKE :q)")
            values["q"] = f"%{params.q}%"
        if params.category:
            filters.append("c.slug = :category")
            values["category"] = params.category
        if params.price_min is not None:
            filters.append("p.price >= :price_min")
            values["price_min"] = params.price_min
        if params.price_max is not None:
            filters.append("p.price <= :price_max")
            values["price_max"] = params.price_max

        where_sql = " AND ".join(filters)
        sort_sql = {
            SORT_PRICE_ASC: "p.price ASC",
            SORT_PRICE_DESC: "p.price DESC",
            SORT_NEWEST: "p.created_at DESC",
            SORT_RATING_DESC: "p.created_at DESC",
            SORT_POPULAR: "p.created_at DESC",
        }.get(params.sort or "", "p.created_at DESC")

        total = await self._session.scalar(
            text(
                f"""
                SELECT COUNT(*)
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {where_sql}
                """
            ),
            values,
        ) or 0

        rows = await self._session.execute(
            text(
                f"""
                SELECT
                    p.id,
                    p.category_id,
                    p.name,
                    p.slug,
                    p.description AS short_description,
                    p.description AS long_description,
                    p.price,
                    p.compare_price AS compare_at_price,
                    p.stock_qty AS stock_quantity,
                    CASE
                        WHEN p.stock_qty <= 0 THEN 'out_of_stock'
                        WHEN p.stock_qty <= 5 THEN 'low_stock'
                        ELSE 'in_stock'
                    END AS availability,
                    p.images,
                    p.created_at,
                    p.updated_at,
                    c.id AS category__id,
                    c.name AS category__name,
                    c.slug AS category__slug,
                    c.description AS category__description
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE {where_sql}
                ORDER BY {sort_sql}
                LIMIT :limit OFFSET :offset
                """
            ),
            values,
        )
        return int(total), [dict(row._mapping) for row in rows]

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Fetch a single active product with its images and tags."""
        query = (
            self._active_products_query()
            .where(Product.id == product_id)
            .options(
                selectinload(Product.images),
                selectinload(Product.tags),
                selectinload(Product.category),
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_related(
        self, product: Product, limit: int
    ) -> list[Product]:
        """Return products from the same category, excluding the given product."""
        query = (
            self._active_products_query()
            .where(Product.category_id == product.category_id)
            .where(Product.id != product.id)
            .order_by(Product.rating_average.desc())
            .limit(limit)
            .options(selectinload(Product.images), selectinload(Product.category))
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_price_range(self) -> Tuple[Decimal, Decimal]:
        """Return (min_price, max_price) across all active products."""
        query = select(
            func.min(Product.price),
            func.max(Product.price),
        ).where(Product.is_active.is_(True))
        row = (await self._session.execute(query)).one()
        return row[0] or Decimal("0"), row[1] or Decimal("0")

    async def get_distinct_skin_types(self) -> list[str]:
        """Return all unique skin_type values present in active products."""
        query = (
            select(Product.skin_type)
            .where(Product.is_active.is_(True))
            .where(Product.skin_type.isnot(None))
            .distinct()
            .order_by(Product.skin_type)
        )
        result = await self._session.execute(query)
        return [row[0] for row in result.all()]

    async def get_featured(self, limit: int) -> list[Product]:
        """Return featured active products ordered by rating."""
        query = (
            self._active_products_query()
            .where(Product.is_featured.is_(True))
            .order_by(Product.rating_average.desc())
            .limit(limit)
            .options(selectinload(Product.images), selectinload(Product.category))
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_any_by_identifier(self, product_id: int | str) -> Optional[Product]:
        query = select(Product).options(
            selectinload(Product.images),
            selectinload(Product.tags),
            selectinload(Product.category),
        )
        if isinstance(product_id, int) or str(product_id).isdigit():
            query = query.where(Product.id == int(product_id))
        else:
            query = query.where(Product.slug == str(product_id))
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_identifier(self, product_id: int | str) -> Optional[Product]:
        query = self._active_products_query().options(
            selectinload(Product.images),
            selectinload(Product.tags),
            selectinload(Product.category),
        )
        if isinstance(product_id, int) or str(product_id).isdigit():
            query = query.where(Product.id == int(product_id))
        else:
            query = query.where(Product.slug == str(product_id))
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create_product(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        return product

    async def save_image(self, product_id: int, image_url: str) -> ProductImage:
        image = ProductImage(product_id=product_id, url=image_url, is_primary=True, sort_order=0)
        self._session.add(image)
        await self._session.flush()
        return image

    async def delete_product(self, product: Product) -> None:
        await self._session.delete(product)
