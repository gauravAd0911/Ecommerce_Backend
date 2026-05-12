"""Repository layer — all database queries."""
import math
from dataclasses import dataclass
 
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.core.constants import ORDER_STATUS_COMPLETED, REVIEW_STATUS_PUBLISHED
from app.models.models import Order, Review
 
 
@dataclass(frozen=True)
class RatingSummaryDTO:
    product_id: str
    total_reviews: int
    average_rating: float
    five_star: int
    four_star: int
    three_star: int
    two_star: int
    one_star: int
    verified_count: int
 
 
@dataclass(frozen=True)
class PaginatedReviews:
    items: list[Review]
    total: int
    page: int
    page_size: int
 
    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.page_size) if self.page_size else 0
 
 
class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
 
    async def is_verified_purchaser(self, user_id: str, product_id: str) -> bool:
        result = await self._session.scalar(
            select(func.count()).select_from(Order).where(
                Order.user_id == user_id,
                Order.product_id == product_id,
                Order.status == ORDER_STATUS_COMPLETED,
            ).limit(1)
        )
        return bool(result)
 
    async def get_by_id(self, review_id: str) -> Review | None:
        return await self._session.get(Review, review_id)
 
    async def list_public(
        self,
        page: int,
        page_size: int,
        product_id: str | None = None,
    ) -> PaginatedReviews:
        filters = [Review.status == REVIEW_STATUS_PUBLISHED]
        if product_id:
            filters.append(Review.product_id == product_id)
        total = await self._session.scalar(select(func.count()).select_from(Review).where(*filters)) or 0
        rows = await self._session.execute(
            select(Review).where(*filters).order_by(Review.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        return PaginatedReviews(items=list(rows.scalars().all()), total=total, page=page, page_size=page_size)

    async def list_for_product(self, product_id: str, page: int, page_size: int) -> PaginatedReviews:
        f = (Review.product_id == product_id, Review.status == REVIEW_STATUS_PUBLISHED)
        total = await self._session.scalar(select(func.count()).select_from(Review).where(*f)) or 0
        rows = await self._session.execute(
            select(Review).where(*f).order_by(Review.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        return PaginatedReviews(items=list(rows.scalars().all()), total=total, page=page, page_size=page_size)
 
    async def list_for_user(self, user_id: str) -> list[Review]:
        rows = await self._session.execute(
            select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc())
        )
        return list(rows.scalars().all())
 
    async def exists_for_user_product(self, user_id: str, product_id: str) -> bool:
        result = await self._session.scalar(
            select(func.count()).select_from(Review)
            .where(Review.user_id == user_id, Review.product_id == product_id).limit(1)
        )
        return bool(result)
 
    async def get_rating_summary(self, product_id: str) -> RatingSummaryDTO | None:
        row = (await self._session.execute(
            text(
                "SELECT product_id, total_reviews, average_rating, "
                "five_star, four_star, three_star, two_star, one_star, verified_count "
                "FROM vw_product_rating_summary WHERE product_id = :pid"
            ),
            {"pid": product_id},
        )).fetchone()
        if row is None:
            return None
        return RatingSummaryDTO(
            product_id=row.product_id, total_reviews=row.total_reviews,
            average_rating=float(row.average_rating),
            five_star=row.five_star, four_star=row.four_star,
            three_star=row.three_star, two_star=row.two_star,
            one_star=row.one_star, verified_count=row.verified_count,
        )
 
    async def create(self, product_id: str, user_id: str, rating: int,
                     title: str, body: str, is_verified: bool) -> Review:
        review = Review(product_id=product_id, user_id=user_id, rating=rating,
                        title=title, body=body, is_verified=is_verified)
        self._session.add(review)
        await self._session.flush()
        await self._session.refresh(review)
        return review
 
    async def patch(self, review: Review, rating: int | None,
                    title: str | None, body: str | None) -> Review:
        if rating is not None: review.rating = rating
        if title  is not None: review.title  = title
        if body   is not None: review.body   = body
        await self._session.flush()
        await self._session.refresh(review)
        return review
