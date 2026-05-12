"""Service layer for the Review Service.

Orchestrates business rules and delegates data access to the repository.
"""

from __future__ import annotations

from app.core.constants import (
    ERR_NOT_VERIFIED_PURCHASER,
    ERR_REVIEW_ALREADY_EXISTS,
    ERR_REVIEW_NOT_FOUND,
    ERR_REVIEW_NOT_OWNED,
)
from app.core.exceptions import (
    ConflictError,
    EligibilityError,
    ForbiddenError,
    NotFoundError,
)
from app.events.publisher import EventPublisher
from app.models.models import Review
from app.repositories.review_repository import (
    PaginatedReviews,
    RatingSummaryDTO,
    ReviewRepository,
)


class ReviewService:
    """Encapsulates business rules for the review domain."""

    def __init__(
        self,
        repository: ReviewRepository,
        publisher: EventPublisher,
    ) -> None:
        self._repo = repository
        self._publisher = publisher

    async def list_for_product(
        self,
        product_id: str,
        page: int,
        page_size: int,
    ) -> PaginatedReviews:
        return await self._repo.list_for_product(product_id, page, page_size)

    async def list_public(
        self,
        page: int,
        page_size: int,
        product_id: str | None = None,
    ) -> PaginatedReviews:
        return await self._repo.list_public(page=page, page_size=page_size, product_id=product_id)

    async def get_rating_summary(self, product_id: str) -> RatingSummaryDTO:
        summary = await self._repo.get_rating_summary(product_id)
        if summary is None:
            raise NotFoundError(ERR_REVIEW_NOT_FOUND)
        return summary

    async def get_by_id(self, review_id: str) -> Review:
        review = await self._repo.get_by_id(review_id)
        if review is None:
            raise NotFoundError(ERR_REVIEW_NOT_FOUND)
        return review

    async def list_for_user(self, user_id: str) -> list[Review]:
        return await self._repo.list_for_user(user_id)

    async def create_review(
        self,
        product_id: str,
        user_id: str,
        rating: int,
        title: str,
        body: str,
    ) -> Review:
        is_verified = await self._repo.is_verified_purchaser(user_id, product_id)
        if not is_verified:
            raise EligibilityError(ERR_NOT_VERIFIED_PURCHASER)

        if await self._repo.exists_for_user_product(user_id, product_id):
            raise ConflictError(ERR_REVIEW_ALREADY_EXISTS)

        review = await self._repo.create(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=body,
            is_verified=is_verified,
        )
        await self._publisher.publish_review_created(review)
        return review

    async def can_review_product(self, product_id: str, user_id: str) -> bool:
        is_verified = await self._repo.is_verified_purchaser(user_id, product_id)
        if not is_verified:
            raise EligibilityError(ERR_NOT_VERIFIED_PURCHASER)
        if await self._repo.exists_for_user_product(user_id, product_id):
            raise ConflictError(ERR_REVIEW_ALREADY_EXISTS)
        return True

    async def patch_review(
        self,
        review_id: str,
        user_id: str,
        rating: int | None,
        title: str | None,
        body: str | None,
    ) -> Review:
        review = await self._repo.get_by_id(review_id)
        if review is None:
            raise NotFoundError(ERR_REVIEW_NOT_FOUND)
        if review.user_id != user_id:
            raise ForbiddenError(ERR_REVIEW_NOT_OWNED)

        updated_review = await self._repo.patch(
            review,
            rating=rating,
            title=title,
            body=body,
        )
        await self._publisher.publish_review_updated(updated_review)
        return updated_review
