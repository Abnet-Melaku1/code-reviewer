from typing import cast

from sqlalchemy import BigInteger, CheckConstraint, Table, UniqueConstraint

from codereviewer.db.models import Repository

TABLE = cast(Table, Repository.__table__)


def test_repository_maps_to_repositories_table() -> None:
    assert Repository.__tablename__ == "repositories"


def test_repository_primary_key_is_id() -> None:
    assert [col.name for col in TABLE.primary_key.columns] == ["id"]


def test_repository_primary_key_is_big_integer() -> None:
    # High-volume tables copy this pattern; a 32-bit PK would be a ceiling risk.
    assert isinstance(TABLE.columns["id"].type, BigInteger)


def test_repository_index_status_is_domain_checked() -> None:
    # The StrEnum column must carry a CHECK constraint, not just be a bare VARCHAR.
    checks = [c for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert checks, "enum column should be enforced by a CHECK constraint"


def test_repository_nullable_fields() -> None:
    assert TABLE.columns["indexed_commit_sha"].nullable is True
    assert TABLE.columns["last_indexed_at"].nullable is True


def test_repository_required_fields_are_not_nullable() -> None:
    for name in ("github_installation_id", "owner", "name", "default_branch", "posting_enabled"):
        assert TABLE.columns[name].nullable is False, name


def test_repository_owner_name_are_unique_together() -> None:
    unique = [c for c in TABLE.constraints if isinstance(c, UniqueConstraint)]
    assert any({col.name for col in uc.columns} == {"owner", "name"} for uc in unique)


def test_repository_installation_id_is_indexed() -> None:
    assert TABLE.columns["github_installation_id"].index is True


def test_repository_has_audit_timestamps() -> None:
    assert "created_at" in TABLE.columns
    assert "updated_at" in TABLE.columns
