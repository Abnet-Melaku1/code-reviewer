from typing import cast

from sqlalchemy import CheckConstraint, ForeignKey, Table

from codereviewer.db.models import Citation

TABLE = cast(Table, Citation.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def _check_texts() -> list[str]:
    return [str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)]


def test_citation_maps_to_citations_table() -> None:
    assert Citation.__tablename__ == "citations"


def test_citation_owned_by_comment_cascades_on_delete() -> None:
    fk = _only_foreign_key("review_comment_id")
    assert fk.column.table.name == "review_comments"
    assert fk.ondelete == "CASCADE"


def test_citation_review_comment_id_is_indexed() -> None:
    assert TABLE.columns["review_comment_id"].index is True


def test_citation_evidence_fks_null_out_on_delete() -> None:
    # A review is a historical record: deleting a re-indexed chunk or a removed convention
    # nulls the reference (grounding goes stale) rather than deleting the past comment.
    for column, target in (("code_chunk_id", "code_chunks"), ("convention_id", "conventions")):
        fk = _only_foreign_key(column)
        assert fk.column.table.name == target
        assert fk.ondelete == "SET NULL"
        assert TABLE.columns[column].nullable is True


def test_citation_evidence_fks_are_indexed() -> None:
    assert TABLE.columns["code_chunk_id"].index is True
    assert TABLE.columns["convention_id"].index is True


def test_citation_kind_is_domain_checked() -> None:
    assert any("kind IN" in text for text in _check_texts())


def test_citation_target_is_consistent_with_kind() -> None:
    # The kind-consistency half of the invariant (non-matching targets must be NULL) is
    # enforced at the DB; "matching target present" stays the Pydantic validator's job.
    joined = " ".join(_check_texts())
    assert "kind = 'code_chunk'" in joined
    assert "kind = 'convention'" in joined
    assert "kind = 'diff_hunk'" in joined
    assert "IS NULL" in joined


def test_citation_required_fields_are_not_nullable() -> None:
    for name in ("review_comment_id", "kind"):
        assert TABLE.columns[name].nullable is False, name
