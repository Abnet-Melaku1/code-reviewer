from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import IndexedFile, Language


def _valid_data() -> dict[str, Any]:
    return {"path": "src/app/main.py", "language": "python", "blob_sha": "abc123"}


def test_indexed_file_construction_and_default_chunk_count() -> None:
    file = IndexedFile(path="src/app/main.py", language=Language.python, blob_sha="abc123")

    assert file.language is Language.python
    assert file.chunk_count == 0


def test_indexed_file_coerces_language_string() -> None:
    file = IndexedFile.model_validate(_valid_data())

    assert file.language is Language.python


@pytest.mark.parametrize("field", ["path", "blob_sha"])
@pytest.mark.parametrize("value", ["", "   "])
def test_indexed_file_rejects_blank_identifiers(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        IndexedFile.model_validate(_valid_data() | {field: value})


def test_indexed_file_rejects_negative_chunk_count() -> None:
    with pytest.raises(ValidationError):
        IndexedFile.model_validate(_valid_data() | {"chunk_count": -1})


def test_indexed_file_rejects_unknown_language() -> None:
    with pytest.raises(ValidationError):
        IndexedFile.model_validate(_valid_data() | {"language": "cobol"})


def test_indexed_file_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        IndexedFile.model_validate(_valid_data() | {"size": 100})


@pytest.mark.parametrize("field", ["path", "language", "blob_sha"])
def test_indexed_file_requires_each_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        IndexedFile.model_validate(data)
