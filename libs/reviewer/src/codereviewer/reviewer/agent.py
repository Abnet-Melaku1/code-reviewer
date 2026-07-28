import os

from sqlalchemy.ext.asyncio import AsyncSession

import codereviewer.db.models as db_models
from codereviewer.providers.base import LlmProvider
from codereviewer.retrieval.diff import parse_diff_hunks
from codereviewer.retrieval.retriever import Retriever
from codereviewer.reviewer.base import get_analyzers, validate_review_comments
from codereviewer.schemas.enums import ReviewStatus, Severity


def get_language_from_path(path: str) -> str:
    """Detect language string from file extension (decoupled from libs.indexer)."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mapping = {
        "py": "python",
        "ts": "typescript",
        "tsx": "typescript",
        "js": "javascript",
        "jsx": "javascript",
        "go": "go",
        "rs": "rust",
        "java": "java",
    }
    return mapping.get(ext, "")


async def run_review(
    session: AsyncSession,
    provider: LlmProvider,
    retriever: Retriever,
    pull_request_id: int,
    repository_id: int,
    diff_content: str,
    commit_sha: str,
    model_name: str = "gpt-4o",
    redis_client: object = None,
) -> db_models.Review:
    """Execute the full review pipeline.

    1. Parse diff into hunks.
    2. Initialize Review record.
    3. Retrieve context and execute analyzers per hunk.
    4. Run grounding validation (filtering comments lying outside target diff lines).
    5. Persist comments and citations transactionally.
    """
    import codereviewer.schemas as schemas

    async def _pub(event: object) -> None:
        if redis_client:
            try:
                # model_dump_json is standard on Pydantic v2
                await redis_client.publish("codereviewer:events", event.model_dump_json())
            except Exception:
                pass

    # 1. Parse diff hunks
    hunks = parse_diff_hunks(diff_content)

    # 2. Create the Review record
    db_review = db_models.Review(
        pull_request_id=pull_request_id,
        head_sha=commit_sha,
        status=ReviewStatus.running,
        model=model_name,
        must_fix=0,
        suggestions=0,
        nits=0,
        tokens_in=0,
        tokens_out=0,
        cost_cents=0,
        latency_ms=0,
    )
    session.add(db_review)
    await session.flush()

    await _pub(
        schemas.ReviewQueuedEvent(
            review_id=db_review.id or 0,
            pull_request_id=pull_request_id,
        )
    )

    await _pub(
        schemas.ReviewProgressEvent(
            review_id=db_review.id or 0,
            phase="Parsing diff hunks...",
            hunks_done=0,
            hunks_total=len(hunks) if hunks else 1,
        )
    )

    if not hunks:
        db_review.status = ReviewStatus.completed
        db_review.summary = "No diff hunks parsed. Nothing to review."
        await _pub(
            schemas.ReviewCompletedEvent(
                review_id=db_review.id or 0,
                summary=db_review.summary,
                must_fix=0,
                suggestions=0,
                nits=0,
            )
        )
        return db_review

    # 3. Retrieve context & analyze hunks
    raw_comments = []
    total_hunks = len(hunks)
    for i, hunk in enumerate(hunks):
        await _pub(
            schemas.ReviewProgressEvent(
                review_id=db_review.id or 0,
                phase=f"Analyzing diff hunk {i + 1}/{total_hunks} ({hunk.file_path})...",
                hunks_done=i,
                hunks_total=total_hunks,
            )
        )
        context = await retriever.retrieve_context(repository_id, hunk)
        lang = get_language_from_path(hunk.file_path)

        for analyzer in get_analyzers():
            if analyzer.applies_to(lang):
                hunk_comments = await analyzer.analyze(hunk, context)
                raw_comments.extend(hunk_comments)

    await _pub(
        schemas.ReviewProgressEvent(
            review_id=db_review.id or 0,
            phase="Saving comments and citations...",
            hunks_done=total_hunks,
            hunks_total=total_hunks,
        )
    )

    # 4. Filter comments (grounding/boundary checks)
    valid_comments = validate_review_comments(raw_comments, hunks)

    # 5. Persist comments and citations
    for comment in valid_comments:
        db_comment = db_models.ReviewComment(
            review_id=db_review.id,
            file_path=comment.file_path,
            line=comment.line,
            side=comment.side,
            severity=comment.severity,
            body=comment.body,
            suggested_patch=comment.suggested_patch,
            posted_to_github=False,
        )
        session.add(db_comment)
        await session.flush()

        await _pub(
            schemas.ReviewCommentEvent(
                review_id=db_review.id or 0,
                comment=comment,
            )
        )

        for citation in comment.citations:
            db_citation = db_models.Citation(
                review_comment_id=db_comment.id,
                kind=citation.kind,
                code_chunk_id=citation.code_chunk_id,
                convention_id=citation.convention_id,
                diff_ref=citation.diff_ref,
            )
            session.add(db_citation)

        # Update metrics
        if comment.severity == Severity.must_fix:
            db_review.must_fix += 1
        elif comment.severity == Severity.suggestion:
            db_review.suggestions += 1
        elif comment.severity == Severity.nit:
            db_review.nits += 1

    db_review.status = ReviewStatus.completed
    db_review.summary = (
        f"Review completed. Identified {db_review.must_fix} critical issues, "
        f"{db_review.suggestions} suggestions, and {db_review.nits} nits."
    )

    await _pub(
        schemas.ReviewCompletedEvent(
            review_id=db_review.id or 0,
            summary=db_review.summary,
            must_fix=db_review.must_fix,
            suggestions=db_review.suggestions,
            nits=db_review.nits,
        )
    )

    return db_review

