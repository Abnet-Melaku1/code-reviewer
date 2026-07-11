from typing import cast

from sqlalchemy import CheckConstraint, ForeignKey, Table, UniqueConstraint

from codereviewer.db.models import Review

TABLE = cast(Table, Review.__table__)


def _only_foreign_key(column: str) -> ForeignKey:
    (fk,) = TABLE.columns[column].foreign_keys
    return fk


def test_review_maps_to_reviews_table() -> None:
    assert Review.__tablename__ == "reviews"


def test_review_references_pull_request_and_cascades_on_delete() -> None:
    fk = _only_foreign_key("pull_request_id")
    assert fk.column.table.name == "pull_requests"
    assert fk.ondelete == "CASCADE"


def test_review_pull_request_id_is_indexed() -> None:
    assert TABLE.columns["pull_request_id"].index is True


def test_review_status_is_domain_checked() -> None:
    checks = [c for c in TABLE.constraints if isinstance(c, CheckConstraint)]
    assert checks, "status enum column should be enforced by a CHECK constraint"


def test_review_is_idempotent_per_pull_request_and_head_sha() -> None:
    unique = [c for c in TABLE.constraints if isinstance(c, UniqueConstraint)]
    assert any({col.name for col in uc.columns} == {"pull_request_id", "head_sha"} for uc in unique)


def _counter_columns() -> list[str]:
    # Counters are the columns _counter() gives a server_default of 0; derive them from the
    # table so a newly added counter can't silently escape the non-negativity check below.
    return [
        col.name
        for col in TABLE.columns
        if col.server_default is not None and str(getattr(col.server_default, "arg", "")) == "0"
    ]


def test_every_counter_column_has_a_non_negative_check() -> None:
    counters = _counter_columns()
    assert counters, "expected to find zero-defaulted counter/metric columns"
    check_text = " ".join(
        str(c.sqltext) for c in TABLE.constraints if isinstance(c, CheckConstraint)
    )
    for name in counters:
        assert f"{name} >= 0" in check_text, name


def test_review_counts_default_to_zero() -> None:
    for name in ("must_fix", "suggestions", "nits", "tokens_in", "tokens_out", "cost_cents"):
        assert TABLE.columns[name].server_default is not None, name


def test_review_summary_is_nullable() -> None:
    assert TABLE.columns["summary"].nullable is True


def test_review_required_fields_are_not_nullable() -> None:
    for name in ("pull_request_id", "head_sha", "status", "model"):
        assert TABLE.columns[name].nullable is False, name
