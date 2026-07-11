from typing import cast

from sqlalchemy import CheckConstraint, ForeignKey, Table

from codereviewer.db.models import Convention

TABLE = cast(Table, Convention.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def _check_texts() -> list[str]:
    return [str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)]


def test_convention_maps_to_conventions_table() -> None:
    assert Convention.__tablename__ == "conventions"


def test_convention_references_repository_and_cascades_on_delete() -> None:
    fk = _only_foreign_key("repository_id")
    assert fk.column.table.name == "repositories"
    assert fk.ondelete == "CASCADE"


def test_convention_repository_id_is_indexed() -> None:
    assert TABLE.columns["repository_id"].index is True


def test_convention_source_is_domain_checked() -> None:
    checks = [c for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert checks, "source enum column should be enforced by a CHECK constraint"


def test_convention_confidence_bounded_to_unit_interval() -> None:
    texts = _check_texts()
    assert any("confidence >= 0" in text for text in texts)
    assert any("confidence <= 1" in text for text in texts)


def test_convention_active_has_server_default() -> None:
    assert TABLE.columns["active"].server_default is not None


def test_convention_example_code_is_nullable() -> None:
    assert TABLE.columns["example_code"].nullable is True


def test_convention_required_fields_are_not_nullable() -> None:
    for name in ("repository_id", "title", "description", "source", "confidence", "active"):
        assert TABLE.columns[name].nullable is False, name
