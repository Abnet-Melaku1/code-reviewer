from typing import cast

from sqlalchemy import CheckConstraint, ForeignKey, Table, UniqueConstraint

from codereviewer.db.models import IndexedFile

TABLE = cast(Table, IndexedFile.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def test_indexed_file_maps_to_indexed_files_table() -> None:
    assert IndexedFile.__tablename__ == "indexed_files"


def test_indexed_file_references_repository_and_cascades_on_delete() -> None:
    fk = _only_foreign_key("repository_id")
    assert fk.column.table.name == "repositories"
    assert fk.ondelete == "CASCADE"


def test_indexed_file_repository_id_is_indexed() -> None:
    assert TABLE.columns["repository_id"].index is True


def test_indexed_file_language_is_domain_checked() -> None:
    checks = [c for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert checks, "language enum column should be enforced by a CHECK constraint"


def test_indexed_file_path_unique_within_repository() -> None:
    unique = [c for c in TABLE.constraints if isinstance(c, UniqueConstraint)]
    assert any({col.name for col in uc.columns} == {"repository_id", "path"} for uc in unique)


def test_indexed_file_required_fields_are_not_nullable() -> None:
    for name in ("repository_id", "path", "language", "blob_sha", "chunk_count"):
        assert TABLE.columns[name].nullable is False, name


def test_indexed_file_chunk_count_defaults_to_zero() -> None:
    assert TABLE.columns["chunk_count"].server_default is not None


def test_indexed_file_enforces_non_negative_chunk_count() -> None:
    texts = [str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert any("chunk_count >= 0" in text for text in texts)
