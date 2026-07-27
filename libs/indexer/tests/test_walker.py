import pathlib

from codereviewer.indexer.walker import compute_git_blob_sha, walk_files
from codereviewer.schemas.enums import Language


def test_walk_files(tmp_path: pathlib.Path) -> None:
    repo = tmp_path

    # 1. Supported source file
    py_file = repo / "main.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    # 2. Unsupported file extension
    txt_file = repo / "README.txt"
    txt_file.write_text("read me", encoding="utf-8")

    # 3. Standard ignore directory (.git)
    git_dir = repo / ".git"
    git_dir.mkdir()
    git_file = git_dir / "config"
    git_file.write_text("some git config", encoding="utf-8")

    # 4. Binary file
    bin_file = repo / "image.png"
    bin_file.write_bytes(b"\x00\x00\x00\x00binary content")

    # 5. Gitignored file and directory
    gitignore = repo / ".gitignore"
    gitignore.write_text("ignored.py\ntemp/", encoding="utf-8")

    ignored_file = repo / "ignored.py"
    ignored_file.write_text("print('ignore me')", encoding="utf-8")

    temp_dir = repo / "temp"
    temp_dir.mkdir()
    temp_file = temp_dir / "helper.py"
    temp_file.write_text("print('temp helper')", encoding="utf-8")

    # Execute walker
    candidates = walk_files(str(repo))

    # Assertions
    # Only main.py should match all filters
    assert len(candidates) == 1
    candidate = candidates[0]

    assert candidate.path == "main.py"
    assert candidate.language == Language.python
    assert candidate.content == "print('hello')"
    assert candidate.blob_sha == compute_git_blob_sha(b"print('hello')")
