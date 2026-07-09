from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import Convention, ConventionSource


def _valid_data() -> dict[str, Any]:
    return {
        "title": "Wrap external calls in a timeout",
        "description": "Every outbound httpx call passes an explicit timeout.",
        "source": "inferred",
        "confidence": 0.8,
    }


def test_convention_construction_and_defaults() -> None:
    convention = Convention.model_validate(_valid_data())

    assert convention.source is ConventionSource.inferred
    assert convention.active is True
    assert convention.example_code is None


def test_convention_coerces_source_string() -> None:
    convention = Convention.model_validate(_valid_data() | {"source": "user_defined"})

    assert convention.source is ConventionSource.user_defined


@pytest.mark.parametrize("confidence", [0.0, 1.0, 0.5])
def test_convention_accepts_confidence_within_bounds(confidence: float) -> None:
    convention = Convention.model_validate(_valid_data() | {"confidence": confidence})

    assert convention.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_convention_rejects_confidence_out_of_bounds(confidence: float) -> None:
    with pytest.raises(ValidationError):
        Convention.model_validate(_valid_data() | {"confidence": confidence})


def test_convention_preserves_example_code_whitespace_verbatim() -> None:
    example = "    if x:\n        do()  \n"
    convention = Convention.model_validate(_valid_data() | {"example_code": example})

    assert convention.example_code == example


@pytest.mark.parametrize("blank", ["", "   \n\t"])
def test_convention_normalizes_blank_example_code_to_none(blank: str) -> None:
    convention = Convention.model_validate(_valid_data() | {"example_code": blank})

    assert convention.example_code is None


@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("value", ["", "   "])
def test_convention_rejects_blank_prose(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Convention.model_validate(_valid_data() | {field: value})


def test_convention_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Convention.model_validate(_valid_data() | {"weight": 1})


@pytest.mark.parametrize("field", ["title", "description", "source", "confidence"])
def test_convention_requires_each_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        Convention.model_validate(data)
