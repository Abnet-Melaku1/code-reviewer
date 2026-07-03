from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import IndexStatus, Repository


def _valid_data() -> dict[str, Any]:
    return {
        "github_installation_id": 42,
        "owner": "acme",
        "name": "webapp",
        "default_branch": "main",
    }


def test_repository_minimal_construction_applies_defaults() -> None:
    repo = Repository(github_installation_id=42, owner="acme", name="webapp", default_branch="main")

    assert repo.index_status is IndexStatus.pending
    assert repo.posting_enabled is False
    assert repo.indexed_commit_sha is None
    assert repo.last_indexed_at is None


def test_repository_accepts_all_fields() -> None:
    now = datetime(2026, 7, 2, tzinfo=UTC)
    repo = Repository(
        github_installation_id=42,
        owner="acme",
        name="webapp",
        default_branch="main",
        index_status=IndexStatus.ready,
        indexed_commit_sha="deadbeef",
        last_indexed_at=now,
        posting_enabled=True,
    )

    assert repo.index_status is IndexStatus.ready
    assert repo.indexed_commit_sha == "deadbeef"
    assert repo.last_indexed_at == now
    assert repo.posting_enabled is True


def test_repository_coerces_status_string_to_enum() -> None:
    repo = Repository.model_validate(_valid_data() | {"index_status": "indexing"})

    assert repo.index_status is IndexStatus.indexing


def test_repository_serializes_enum_as_string() -> None:
    repo = Repository(github_installation_id=42, owner="acme", name="webapp", default_branch="main")

    assert repo.model_dump()["index_status"] == "pending"


@pytest.mark.parametrize("field", ["owner", "name", "default_branch"])
@pytest.mark.parametrize("value", ["", "   "])
def test_repository_rejects_blank_identifier(field: str, value: str) -> None:
    # Whitespace-only must fail too: str_strip_whitespace collapses "   " to "" -> min_length.
    with pytest.raises(ValidationError):
        Repository.model_validate(_valid_data() | {field: value})


def test_repository_rejects_non_positive_installation_id() -> None:
    with pytest.raises(ValidationError):
        Repository.model_validate(_valid_data() | {"github_installation_id": 0})


def test_repository_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Repository.model_validate(_valid_data() | {"stars": 100})


@pytest.mark.parametrize("field", ["github_installation_id", "owner", "name", "default_branch"])
def test_repository_requires_each_identity_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        Repository.model_validate(data)
