from codereviewer.indexer.chunker import chunk_code
from codereviewer.schemas.enums import Language, SymbolKind


def test_python_chunker_basic() -> None:
    code = """class Calculator:
    def add(self, a, b):
        return a + b

def get_version():
    return "1.0.0"
"""
    chunks = chunk_code(code, Language.python, path="math_ops.py")

    # We expect 3 chunks: class, method, function
    assert len(chunks) == 3

    # Verify class chunk
    class_chunk = next(c for c in chunks if c.symbol_kind == SymbolKind.class_)
    assert class_chunk.symbol_name == "Calculator"
    assert class_chunk.start_line == 1
    assert class_chunk.end_line == 3
    assert "class Calculator:" in class_chunk.content
    assert class_chunk.token_count > 0

    # Verify method chunk
    method_chunk = next(c for c in chunks if c.symbol_kind == SymbolKind.method)
    assert method_chunk.symbol_name == "Calculator.add"
    assert method_chunk.start_line == 2
    assert method_chunk.end_line == 3
    assert "def add" in method_chunk.content
    assert method_chunk.token_count > 0

    # Verify function chunk
    func_chunk = next(c for c in chunks if c.symbol_kind == SymbolKind.function)
    assert func_chunk.symbol_name == "get_version"
    assert func_chunk.start_line == 5
    assert func_chunk.end_line == 6
    assert "def get_version():" in func_chunk.content
    assert func_chunk.token_count > 0


def test_sliding_window_fallback() -> None:
    code = "\n".join(f"line {i}" for i in range(1, 101))
    chunks = chunk_code(code, Language.go, path="main.go")

    # Defaults: window_size = 50, overlap = 10
    # Chunk 1: lines 1-50
    # Chunk 2: lines 41-90
    # Chunk 3: lines 81-100
    assert len(chunks) == 3

    assert chunks[0].symbol_kind == SymbolKind.block
    assert chunks[0].symbol_name is None
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 50
    assert chunks[0].token_count > 0

    assert chunks[1].start_line == 41
    assert chunks[1].end_line == 90

    assert chunks[2].start_line == 81
    assert chunks[2].end_line == 100


def test_empty_content_returns_no_chunks() -> None:
    assert chunk_code("", Language.python) == []
    assert chunk_code("   \n  \t ", Language.python) == []
