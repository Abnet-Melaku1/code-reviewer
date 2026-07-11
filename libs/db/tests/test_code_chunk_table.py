from typing import cast

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Index, Table

from codereviewer.db.models import EMBEDDING_DIM, CodeChunk

TABLE = cast(Table, CodeChunk.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def _embedding_index() -> Index:
    (index,) = [i for i in TABLE.indexes if "embedding" in {c.name for c in i.columns}]
    return index


def test_code_chunk_maps_to_code_chunks_table() -> None:
    assert CodeChunk.__tablename__ == "code_chunks"


def test_code_chunk_references_indexed_file_and_cascades_on_delete() -> None:
    fk = _only_foreign_key("indexed_file_id")
    assert fk.column.table.name == "indexed_files"
    assert fk.ondelete == "CASCADE"


def test_code_chunk_indexed_file_id_is_indexed() -> None:
    assert TABLE.columns["indexed_file_id"].index is True


def _check_texts() -> list[str]:
    return [str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)]


def test_code_chunk_symbol_kind_is_domain_checked() -> None:
    checks = [c for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert checks, "symbol_kind enum column should be enforced by a CHECK constraint"


def test_code_chunk_enforces_line_span_invariant() -> None:
    # The spec-named end_line >= start_line invariant is enforced at the DB, not only Pydantic.
    assert any("end_line >= start_line" in text for text in _check_texts())


def test_code_chunk_enforces_positive_bounds() -> None:
    texts = _check_texts()
    assert any("start_line >= 1" in text for text in texts)
    assert any("token_count >= 1" in text for text in texts)


def test_code_chunk_embedding_is_a_fixed_dimension_vector() -> None:
    embedding = TABLE.columns["embedding"]
    assert isinstance(embedding.type, Vector)
    assert embedding.type.dim == EMBEDDING_DIM
    assert embedding.nullable is False


def test_code_chunk_embedding_has_hnsw_cosine_index() -> None:
    index = _embedding_index()
    assert index.dialect_kwargs["postgresql_using"] == "hnsw"
    assert index.dialect_kwargs["postgresql_ops"] == {"embedding": "vector_cosine_ops"}


def test_code_chunk_symbol_name_is_nullable() -> None:
    assert TABLE.columns["symbol_name"].nullable is True


def test_code_chunk_required_fields_are_not_nullable() -> None:
    for name in (
        "indexed_file_id",
        "symbol_kind",
        "start_line",
        "end_line",
        "content",
        "token_count",
    ):
        assert TABLE.columns[name].nullable is False, name
