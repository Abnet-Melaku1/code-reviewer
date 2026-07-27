"""Integration tests that run the ORM against a real Postgres via testcontainers.

Two fixtures so coverage degrades gracefully: relational tables run against plain Postgres
(anywhere), while the pgvector-specific test needs the pgvector image and skips without it.
Both are excluded from the default gate (see the ``integration`` marker) — run with
``pytest -m integration``.

Set ``CODEREVIEWER_REQUIRE_INTEGRATION=1`` (CI does) to turn a missing image into a failure
instead of a silent skip — otherwise the pgvector-only invariants (the grounding cluster's
SET NULL / target CHECK / cascade) could be validated nowhere.
"""

import os
import subprocess
from collections.abc import Iterator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.postgres import PostgresContainer

from codereviewer.db.base import Base
from codereviewer.db.models import (
    EMBEDDING_DIM,
    CodeChunk,
    Convention,
    IndexedFile,
    PullRequest,
    Repository,
    Review,
    ReviewComment,
)
from codereviewer.db.session import create_session_factory, make_engine
from codereviewer.schemas import ConventionSource, DiffSide, Language, Severity, SymbolKind

pytestmark = pytest.mark.integration

_REQUIRE_INTEGRATION = os.environ.get("CODEREVIEWER_REQUIRE_INTEGRATION") == "1"

# Tables create_all cannot build without the pgvector extension: code_chunks holds the Vector
# column, and citations is excluded transitively because its FK targets code_chunks.
_TABLES_REQUIRING_PGVECTOR = {"code_chunks", "citations"}
_PLAIN_POSTGRES_TABLES = [
    t for name, t in Base.metadata.tables.items() if name not in _TABLES_REQUIRING_PGVECTOR
]


def _image_available(image: str) -> bool:
    # Local-only check (no network) so a missing image skips cleanly instead of hanging on a
    # pull. CI pre-pulls the images it wants to exercise; a dev without pgvector still runs
    # the relational test.
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _start(image: str) -> Iterator[str]:
    if not _image_available(image):
        message = f"{image} not available locally"
        if _REQUIRE_INTEGRATION:
            pytest.fail(
                f"{message}; CODEREVIEWER_REQUIRE_INTEGRATION=1 requires it (pre-pull in CI)"
            )
        pytest.skip(f"{message} (pull it, or run in CI)")
    # Avoid pulling testcontainers' "ryuk" reaper image in offline environments; the
    # context-managed container still stops on teardown. setdefault lets CI force ryuk back on.
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    container = PostgresContainer(image, driver="asyncpg")
    try:
        container.start()
    except Exception as exc:  # docker down / start failure — skip, don't fail the suite
        pytest.skip(f"could not start {image}: {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture(scope="module")
def relational_url() -> Iterator[str]:
    yield from _start("postgres:16")


@pytest.fixture(scope="module")
def pgvector_url() -> Iterator[str]:
    yield from _start("pgvector/pgvector:pg16")


async def _prepared_engine(url: str, *, with_vector: bool) -> AsyncEngine:
    """Return an engine over a freshly (re)created schema, so tests sharing the module
    container start from a clean database rather than seeing each other's rows."""
    engine = make_engine(url)
    tables = None if with_vector else _PLAIN_POSTGRES_TABLES
    async with engine.begin() as conn:
        if with_vector:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.run_sync(lambda c: Base.metadata.drop_all(c, tables=tables))

    if with_vector:
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["DATABASE_URL"] = url
        db_dir = os.path.dirname(os.path.dirname(__file__))
        try:
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=db_dir,
                env=env,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print("Alembic stdout:", e.stdout.decode())
            print("Alembic stderr:", e.stderr.decode())
            raise
    else:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    return engine


async def test_relational_round_trip_constraints_and_cascade(relational_url: str) -> None:
    engine = await _prepared_engine(relational_url, with_vector=False)
    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            repo = Repository(
                github_installation_id=1, owner="acme", name="web", default_branch="main"
            )
            session.add(repo)
            await session.flush()
            session.add_all(
                [
                    IndexedFile(
                        repository_id=repo.id,
                        path="src/app.py",
                        language=Language.python,
                        blob_sha="blob1",
                    ),
                    Convention(
                        repository_id=repo.id,
                        title="Timeouts",
                        description="Always pass a timeout.",
                        source=ConventionSource.inferred,
                        confidence=0.9,
                    ),
                ]
            )
            pr = PullRequest(
                repository_id=repo.id, number=1, head_sha="h", base_sha="b", title="t", author="me"
            )
            session.add(pr)
            await session.flush()
            review = Review(pull_request_id=pr.id, head_sha="h", model="claude-opus-4-8")
            session.add(review)
            await session.flush()
            session.add(
                ReviewComment(
                    review_id=review.id,
                    file_path="src/app.py",
                    line=10,
                    side=DiffSide.right,
                    severity=Severity.must_fix,
                    body="Needs a timeout.",
                )
            )
            await session.commit()

        # The DB enforces a domain CHECK, not just Pydantic.
        async with factory() as session:
            session.add(
                PullRequest(
                    repository_id=repo.id,
                    number=0,
                    head_sha="h2",
                    base_sha="b",
                    title="t",
                    author="me",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

        # Deleting the repository cascades to its children via ON DELETE CASCADE.
        async with factory() as session:
            repo_again = await session.get(Repository, repo.id)
            assert repo_again is not None
            await session.delete(repo_again)
            await session.commit()

        async with factory() as session:
            remaining = await session.scalar(
                select(func.count())
                .select_from(PullRequest)
                .where(PullRequest.repository_id == repo.id)
            )
            assert remaining == 0
    finally:
        await engine.dispose()


async def test_pgvector_round_trip_and_cosine_search(pgvector_url: str) -> None:
    engine = await _prepared_engine(pgvector_url, with_vector=True)
    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            repo = Repository(
                github_installation_id=2, owner="acme", name="api", default_branch="main"
            )
            session.add(repo)
            await session.flush()
            file = IndexedFile(
                repository_id=repo.id, path="m.py", language=Language.python, blob_sha="b"
            )
            session.add(file)
            await session.flush()

            near = CodeChunk(
                indexed_file_id=file.id,
                symbol_kind=SymbolKind.function,
                start_line=1,
                end_line=2,
                content="def a(): ...",
                embedding=[1.0] + [0.0] * (EMBEDDING_DIM - 1),
                token_count=3,
            )
            far = CodeChunk(
                indexed_file_id=file.id,
                symbol_kind=SymbolKind.function,
                start_line=3,
                end_line=4,
                content="def b(): ...",
                embedding=[0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2),
                token_count=3,
            )
            session.add_all([near, far])
            await session.commit()
            near_id = near.id

            query = [1.0] + [0.0] * (EMBEDDING_DIM - 1)
            nearest = await session.scalar(
                select(CodeChunk).order_by(CodeChunk.embedding.cosine_distance(query)).limit(1)
            )
            assert nearest is not None
            assert nearest.id == near_id
    finally:
        await engine.dispose()
