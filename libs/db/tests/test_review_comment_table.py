from typing import cast

from sqlalchemy import CheckConstraint, ForeignKey, Table

from codereviewer.db.models import ReviewComment

TABLE = cast(Table, ReviewComment.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def _check_texts() -> list[str]:
    return [str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)]


def test_review_comment_maps_to_review_comments_table() -> None:
    assert ReviewComment.__tablename__ == "review_comments"


def test_review_comment_references_review_and_cascades_on_delete() -> None:
    fk = _only_foreign_key("review_id")
    assert fk.column.table.name == "reviews"
    assert fk.ondelete == "CASCADE"


def test_review_comment_review_id_is_indexed() -> None:
    assert TABLE.columns["review_id"].index is True


def test_review_comment_side_and_severity_are_domain_checked() -> None:
    texts = _check_texts()
    assert any("side IN" in text for text in texts)
    assert any("severity IN" in text for text in texts)


def test_review_comment_line_is_positive() -> None:
    assert any("line >= 1" in text for text in _check_texts())


def test_review_comment_github_id_positive_when_present() -> None:
    assert any("github_comment_id > 0" in text for text in _check_texts())


def test_review_comment_optional_fields_are_nullable() -> None:
    assert TABLE.columns["suggested_patch"].nullable is True
    assert TABLE.columns["github_comment_id"].nullable is True


def test_review_comment_posted_flag_has_server_default() -> None:
    assert TABLE.columns["posted_to_github"].server_default is not None


def test_review_comment_required_fields_are_not_nullable() -> None:
    for name in ("review_id", "file_path", "line", "side", "severity", "body"):
        assert TABLE.columns[name].nullable is False, name
