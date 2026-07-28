from typing import Annotated, Literal

from pydantic import Field

from codereviewer.schemas.enums import IndexStatus
from codereviewer.schemas.models import DomainModel, ReviewComment


class IndexProgressEvent(DomainModel):
    """Event sent when indexing a repository is in progress."""

    type: Literal["index.progress"] = "index.progress"
    repository_id: int
    phase: str
    files_done: int
    files_total: int


class IndexStatusEvent(DomainModel):
    """Event sent when repository index status transitions."""

    type: Literal["index.status"] = "index.status"
    repository_id: int
    index_status: IndexStatus


class ReviewQueuedEvent(DomainModel):
    """Event sent when a review run job is accepted and queued."""

    type: Literal["review.queued"] = "review.queued"
    review_id: int
    pull_request_id: int


class ReviewProgressEvent(DomainModel):
    """Event sent when PR review is in progress."""

    type: Literal["review.progress"] = "review.progress"
    review_id: int
    phase: str
    hunks_done: int
    hunks_total: int


class ReviewCommentEvent(DomainModel):
    """Event sent when a review comment is produced and grounded."""

    type: Literal["review.comment"] = "review.comment"
    review_id: int
    comment: ReviewComment


class ReviewCompletedEvent(DomainModel):
    """Event sent when a review run completes successfully."""

    type: Literal["review.completed"] = "review.completed"
    review_id: int
    summary: str
    must_fix: int
    suggestions: int
    nits: int


class ReviewFailedEvent(DomainModel):
    """Event sent when a review run fails."""

    type: Literal["review.failed"] = "review.failed"
    review_id: int
    error: str


# Discriminated union of all WebSocket events for FastAPI / generated TypeScript contract
WebSocketEvent = Annotated[
    IndexProgressEvent
    | IndexStatusEvent
    | ReviewQueuedEvent
    | ReviewProgressEvent
    | ReviewCommentEvent
    | ReviewCompletedEvent
    | ReviewFailedEvent,
    Field(discriminator="type"),
]
