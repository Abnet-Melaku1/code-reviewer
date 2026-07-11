from typing import cast

from sqlalchemy import CheckConstraint, ForeignKey, Table, UniqueConstraint

from codereviewer.db.models import PullRequest

TABLE = cast(Table, PullRequest.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def test_pull_request_maps_to_pull_requests_table() -> None:
    assert PullRequest.__tablename__ == "pull_requests"


def test_pull_request_references_repository_and_cascades_on_delete() -> None:
    fk = _only_foreign_key("repository_id")
    assert fk.column.table.name == "repositories"
    assert fk.ondelete == "CASCADE"


def test_pull_request_repository_id_is_indexed() -> None:
    assert TABLE.columns["repository_id"].index is True


def test_pull_request_state_is_domain_checked() -> None:
    checks = [c for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert checks, "state enum column should be enforced by a CHECK constraint"


def test_pull_request_number_unique_within_repository() -> None:
    unique = [c for c in TABLE.constraints if isinstance(c, UniqueConstraint)]
    assert any({col.name for col in uc.columns} == {"repository_id", "number"} for uc in unique)


def test_pull_request_number_is_positive() -> None:
    texts = [str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert any("number >= 1" in text for text in texts)


def test_pull_request_required_fields_are_not_nullable() -> None:
    for name in ("repository_id", "number", "head_sha", "base_sha", "title", "author", "state"):
        assert TABLE.columns[name].nullable is False, name
