import pytest

from codereviewer.schemas import Severity


def test_severity_has_exactly_the_canonical_values_in_order() -> None:
    assert [s.value for s in Severity] == ["must_fix", "suggestion", "nit", "context"]


def test_severity_is_a_string_enum() -> None:
    # Members compare equal to their string value so severities serialize as plain strings.
    assert Severity.must_fix == "must_fix"


def test_severity_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        Severity("blocker")
