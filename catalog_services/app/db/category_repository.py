"""Category repository: encapsulates all database access for categories."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category


class CategoryRepository:
    """Data-access layer for Category entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_active(self) -> list[Category]:
        """Return all active categories ordered by sort_order."""
        query = (
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order, Category.name)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_top(self, limit: int) -> list[Category]:
        """Return the top-level active categories (no parent) for the home page."""
        query = (
            select(Category)
            .where(Category.is_active.is_(True))
            .where(Category.parent_id.is_(None))
            .order_by(Category.sort_order, Category.name)
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_slug_or_name(self, value: str) -> Category | None:
        normalized = value.strip().lower()
        query = select(Category).where(
            (Category.slug == normalized) | (Category.name.ilike(value.strip()))
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, *, name: str, slug: str) -> Category:
        category = Category(name=name.strip(), slug=slug.strip().lower(), is_active=True)
        self._session.add(category)
        await self._session.flush()
        return category
