from typing import Any

import pytest
from pydantic import ValidationError

from codereviewer.schemas import CodeChunk, SymbolKind


def _valid_data() -> dict[str, Any]:
    return {
        "symbol_kind": "function",
        "symbol_name": "main",
        "start_line": 10,
        "end_line": 20,
        "content": "def main():\n    pass\n",
        "token_count": 8,
    }


def test_code_chunk_construction() -> None:
    chunk = CodeChunk.model_validate(_valid_data())

    assert chunk.symbol_kind is SymbolKind.function
    assert chunk.symbol_name == "main"
    assert chunk.start_line == 10
    assert chunk.end_line == 20


def test_code_chunk_symbol_name_is_optional() -> None:
    chunk = CodeChunk.model_validate(_valid_data() | {"symbol_name": None})

    assert chunk.symbol_name is None


def test_code_chunk_preserves_content_whitespace_verbatim() -> None:
    content = "    indented = True  \n\treturn indented\n"
    chunk = CodeChunk.model_validate(_valid_data() | {"content": content})

    assert chunk.content == content


def test_code_chunk_allows_single_line_span() -> None:
    chunk = CodeChunk.model_validate(_valid_data() | {"start_line": 5, "end_line": 5})

    assert chunk.start_line == chunk.end_line == 5


def test_code_chunk_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        CodeChunk.model_validate(_valid_data() | {"start_line": 20, "end_line": 10})


@pytest.mark.parametrize("field", ["start_line", "end_line"])
def test_code_chunk_rejects_non_positive_line(field: str) -> None:
    with pytest.raises(ValidationError):
        CodeChunk.model_validate(_valid_data() | {field: 0})


@pytest.mark.parametrize("content", ["", "   \n\t "])
def test_code_chunk_rejects_empty_or_blank_content(content: str) -> None:
    with pytest.raises(ValidationError):
        CodeChunk.model_validate(_valid_data() | {"content": content})


def test_code_chunk_rejects_empty_symbol_name() -> None:
    # symbol_name is optional, but an empty string is a meaningless name — use None instead.
    with pytest.raises(ValidationError):
        CodeChunk.model_validate(_valid_data() | {"symbol_name": ""})


def test_code_chunk_rejects_non_positive_token_count() -> None:
    with pytest.raises(ValidationError):
        CodeChunk.model_validate(_valid_data() | {"token_count": 0})


def test_code_chunk_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        CodeChunk.model_validate(_valid_data() | {"embedding": [0.1, 0.2]})


@pytest.mark.parametrize(
    "field", ["symbol_kind", "start_line", "end_line", "content", "token_count"]
)
def test_code_chunk_requires_each_non_optional_field(field: str) -> None:
    data = _valid_data()
    del data[field]

    with pytest.raises(ValidationError):
        CodeChunk.model_validate(data)
