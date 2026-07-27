import tiktoken
import tree_sitter_languages  # type: ignore[import-untyped]
from tree_sitter import Node, Parser

from codereviewer.schemas.enums import Language, SymbolKind
from codereviewer.schemas.models import CodeChunk


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken's cl100k_base tokenizer.

    Falls back to a whitespace-based word count heuristic if tiktoken fails.
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Simple word count as safety fallback
        return len(text.split())


def chunk_sliding_window(
    content: str,
    window_size: int = 50,
    overlap: int = 10,
) -> list[CodeChunk]:
    """Fall back to a sliding window of lines for unsupported languages."""
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[CodeChunk] = []
    num_lines = len(lines)

    start_idx = 0
    while start_idx < num_lines:
        end_idx = min(start_idx + window_size, num_lines)
        chunk_lines = lines[start_idx:end_idx]
        chunk_content = "\n".join(chunk_lines)

        if chunk_content.strip():
            start_line = start_idx + 1
            end_line = end_idx
            chunks.append(
                CodeChunk(
                    symbol_kind=SymbolKind.block,
                    symbol_name=None,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    token_count=count_tokens(chunk_content),
                )
            )

        if end_idx == num_lines:
            break

        start_idx += window_size - overlap
        if start_idx <= 0 or (window_size - overlap) <= 0:
            start_idx = end_idx

    return chunks


def _traverse_py_tree(
    node: Node,
    lines: list[str],
    parent_class_name: str | None = None,
    chunks: list[CodeChunk] | None = None,
) -> list[CodeChunk]:
    """Recursively traverse Python AST nodes to collect class, method, and function chunks."""
    if chunks is None:
        chunks = []

    is_class = node.type == "class_definition"
    is_func = node.type == "function_definition"

    next_parent_class = parent_class_name

    if is_class or is_func:
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf-8") if name_node and name_node.text else None

        if is_class:
            kind = SymbolKind.class_
            symbol_name = name
            next_parent_class = name
        else:
            if parent_class_name:
                kind = SymbolKind.method
                symbol_name = f"{parent_class_name}.{name}" if name else None
            else:
                kind = SymbolKind.function
                symbol_name = name

        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        chunk_lines = lines[start_line - 1 : end_line]
        chunk_content = "\n".join(chunk_lines)

        if chunk_content.strip():
            chunks.append(
                CodeChunk(
                    symbol_kind=kind,
                    symbol_name=symbol_name,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    token_count=count_tokens(chunk_content),
                )
            )

    # Traverse children recursively
    for child in node.children:
        _traverse_py_tree(child, lines, next_parent_class, chunks)

    return chunks


def chunk_python(content: str) -> list[CodeChunk]:
    """Parse and chunk a Python file using tree-sitter."""
    try:
        py_lang = tree_sitter_languages.get_language("python")
        parser = Parser()
        parser.set_language(py_lang)
    except Exception:
        # Fall back to sliding window if tree-sitter loading fails
        return chunk_sliding_window(content)

    tree = parser.parse(content.encode("utf-8"))
    lines = content.splitlines()

    return _traverse_py_tree(tree.root_node, lines)


def chunk_code(
    content: str,
    language: Language,
    path: str = "unknown",
) -> list[CodeChunk]:
    """Parse and chunk source code, yielding a list of CodeChunks.

    Uses tree-sitter AST-aware chunking for supported languages (starting with Python),
    and falls back to sliding-window chunking for other/unsupported languages.
    """
    if not content.strip():
        return []

    if language == Language.python:
        return chunk_python(content)

    # Fallback to sliding window for unsupported languages
    return chunk_sliding_window(content)
