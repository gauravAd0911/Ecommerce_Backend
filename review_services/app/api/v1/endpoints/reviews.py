"""FastAPI route handlers for the review service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserId
from app.core.config import settings
from app.core.exceptions import ConflictError, EligibilityError, ForbiddenError, NotFoundError
from app.db.session import get_db_session
from app.events.publisher import EventPublisher
from app.repositories.review_repository import ReviewRepository
from app.schemas.schemas import (
    PaginatedReviewsResponse,
    RatingSummaryResponse,
    ReviewCreateRequest,
    ReviewEligibilityResponse,
    ReviewPatchRequest,
    ReviewResponse,
)
from app.services.review_service import ReviewService

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _get_service(session: DbSession) -> ReviewService:
    return ReviewService(
        repository=ReviewRepository(session),
        publisher=EventPublisher(session),
    )


ReviewSvc = Annotated[ReviewService, Depends(_get_service)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=settings.max_page_size)]


@router.get("/products/{product_id}/reviews", response_model=PaginatedReviewsResponse, tags=["Reviews"])
async def list_product_reviews(
    product_id: str,
    service: ReviewSvc,
    page: PageNumber = 1,
    page_size: PageSize = settings.default_page_size,
) -> PaginatedReviewsResponse:
    paginated_reviews = await service.list_for_product(product_id, page, page_size)
    return PaginatedReviewsResponse(
        items=[ReviewResponse.model_validate(review) for review in paginated_reviews.items],
        total=paginated_reviews.total,
        page=paginated_reviews.page,
        page_size=paginated_reviews.page_size,
        pages=paginated_reviews.pages,
    )


@router.get("/products/{product_id}/rating-summary", response_model=RatingSummaryResponse, tags=["Reviews"])
async def get_rating_summary(product_id: str, service: ReviewSvc) -> RatingSummaryResponse:
    try:
        summary = await service.get_rating_summary(product_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RatingSummaryResponse(**summary.__dict__)


@router.get("/reviews/eligibility/{product_id}", response_model=ReviewEligibilityResponse, tags=["Reviews"])
async def get_review_eligibility(
    product_id: str,
    service: ReviewSvc,
    user_id: CurrentUserId,
) -> ReviewEligibilityResponse:
    try:
        if await service.can_review_product(product_id=product_id, user_id=user_id):
            return ReviewEligibilityResponse(can_review=True)
    except EligibilityError as exc:
        return ReviewEligibilityResponse(can_review=False, reason=str(exc))
    except ConflictError as exc:
        return ReviewEligibilityResponse(can_review=False, reason=str(exc))
    return ReviewEligibilityResponse(can_review=False, reason="Review is not allowed for this product.")


@router.get("/reviews", response_model=PaginatedReviewsResponse, tags=["Reviews"])
async def list_reviews(
    service: ReviewSvc,
    product_id: str | None = Query(default=None),
    page: PageNumber = 1,
    page_size: PageSize = settings.default_page_size,
) -> PaginatedReviewsResponse:
    paginated_reviews = await service.list_public(
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedReviewsResponse(
        items=[ReviewResponse.model_validate(review) for review in paginated_reviews.items],
        total=paginated_reviews.total,
        page=paginated_reviews.page,
        page_size=paginated_reviews.page_size,
        pages=paginated_reviews.pages,
    )


@router.post("/products/{product_id}/reviews", response_model=ReviewResponse, status_code=201, tags=["Reviews"])
async def create_review(
    product_id: str,
    payload: ReviewCreateRequest,
    service: ReviewSvc,
    user_id: CurrentUserId,
) -> ReviewResponse:
    try:
        review = await service.create_review(
            product_id=product_id,
            user_id=user_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
        )
    except EligibilityError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewResponse.model_validate(review)


@router.post("/account/reviews", response_model=ReviewResponse, status_code=201, tags=["Reviews"])
async def create_review_compat(
    payload: dict,
    service: ReviewSvc,
    user_id: CurrentUserId,
) -> ReviewResponse:
    product_id = payload.get("product_id") or payload.get("productId")
    rating = payload.get("rating")
    comment = payload.get("comment") or payload.get("body")
    title = payload.get("title") or (comment[:50] if comment else "")
    if not product_id or rating is None or comment is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="product_id, rating, and comment are required",
        )
    try:
        review = await service.create_review(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            body=comment,
        )
    except EligibilityError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewResponse.model_validate(review)


@router.get("/account/reviews", response_model=list[ReviewResponse], tags=["Reviews"])
async def get_my_reviews_compat(service: ReviewSvc, user_id: CurrentUserId) -> list[ReviewResponse]:
    return [ReviewResponse.model_validate(review) for review in await service.list_for_user(user_id)]


@router.get("/account/reviews/{review_id}", response_model=ReviewResponse, tags=["Reviews"])
async def get_review_compat(review_id: str, service: ReviewSvc) -> ReviewResponse:
    return await get_review(review_id, service)


@router.get("/reviews/public", response_model=PaginatedReviewsResponse, tags=["Reviews"])
async def list_public_reviews(
    service: ReviewSvc,
    product_id: str = Query(...),
    page: PageNumber = 1,
    page_size: PageSize = settings.default_page_size,
) -> PaginatedReviewsResponse:
    paginated_reviews = await service.list_for_product(product_id, page, page_size)
    return PaginatedReviewsResponse(
        items=[ReviewResponse.model_validate(review) for review in paginated_reviews.items],
        total=paginated_reviews.total,
        page=paginated_reviews.page,
        page_size=paginated_reviews.page_size,
        pages=paginated_reviews.pages,
    )


@router.patch("/reviews/{review_id}", response_model=ReviewResponse, tags=["Reviews"])
async def patch_review(
    review_id: str,
    payload: ReviewPatchRequest,
    service: ReviewSvc,
    user_id: CurrentUserId,
) -> ReviewResponse:
    try:
        review = await service.patch_review(
            review_id=review_id,
            user_id=user_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ForbiddenError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ReviewResponse.model_validate(review)


@router.get("/users/me/reviews", response_model=list[ReviewResponse], tags=["Reviews"])
async def list_my_reviews(service: ReviewSvc, user_id: CurrentUserId) -> list[ReviewResponse]:
    return [ReviewResponse.model_validate(review) for review in await service.list_for_user(user_id)]


@router.get("/reviews/{review_id}", response_model=ReviewResponse, tags=["Reviews"])
async def get_review(review_id: str, service: ReviewSvc) -> ReviewResponse:
    try:
        review = await service.get_by_id(review_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReviewResponse.model_validate(review)
