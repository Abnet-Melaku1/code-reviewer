import hashlib
import os
from dataclasses import dataclass

import pathspec

from codereviewer.schemas.enums import Language


@dataclass
class FileCandidate:
    """A file candidate to be indexed."""

    path: str
    language: Language
    blob_sha: str
    content: str


def compute_git_blob_sha(content_bytes: bytes) -> str:
    """Compute the git-compatible blob SHA-1 of the file content bytes."""
    header = f"blob {len(content_bytes)}\0".encode()
    hasher = hashlib.sha1()
    hasher.update(header)
    hasher.update(content_bytes)
    return hasher.hexdigest()


def is_binary_file(filepath: str) -> bool:
    """Check if a file is binary by searching for null bytes in its first block."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            return b"\0" in chunk
    except Exception:
        return True


class GitIgnoreChecker:
    """Checker that parses and respects gitignore rules for path exclusion."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.spec = self._load_gitignore()

    def _load_gitignore(self) -> pathspec.PathSpec | None:  # type: ignore[type-arg]
        gitignore_path = os.path.join(self.repo_path, ".gitignore")
        if not os.path.exists(gitignore_path):
            return None
        try:
            with open(gitignore_path, encoding="utf-8") as f:
                lines = f.readlines()
            return pathspec.PathSpec.from_lines("gitignore", lines)
        except Exception:
            return None

    def is_ignored(self, relative_path: str) -> bool:
        """Check if a repo-relative path is matched by gitignore or standard ignore lists."""
        normalized = relative_path.replace("\\", "/")
        parts = normalized.split("/")

        # Standard directories that are always ignored in the index pipeline
        always_ignore = {
            ".git",
            "node_modules",
            "vendor",
            ".venv",
            "__pycache__",
            "build",
            "dist",
        }
        if any(part in always_ignore for part in parts):
            return True

        if self.spec:
            return self.spec.match_file(normalized)
        return False


def walk_files(repo_path: str) -> list[FileCandidate]:
    """Walk a local directory recursively, extracting valid source files for indexing.

    Respects gitignore rules, skips binary/vendored/generated directories, and detects
    the language based on file extension.
    """
    checker = GitIgnoreChecker(repo_path)
    candidates: list[FileCandidate] = []

    ext_map = {
        ".py": Language.python,
        ".ts": Language.typescript,
        ".tsx": Language.typescript,
        ".js": Language.javascript,
        ".jsx": Language.javascript,
        ".go": Language.go,
        ".rs": Language.rust,
        ".java": Language.java,
    }

    for root, dirs, files in os.walk(repo_path):
        # Prune ignored/standard-ignored directories in-place to avoid unnecessary walks
        pruned_dirs = []
        for d in dirs:
            dir_path = os.path.join(root, d)
            rel_dir_path = os.path.relpath(dir_path, repo_path)
            if checker.is_ignored(rel_dir_path):
                continue
            pruned_dirs.append(d)
        dirs[:] = pruned_dirs

        for file in files:
            file_path = os.path.join(root, file)
            rel_file_path = os.path.relpath(file_path, repo_path)

            if checker.is_ignored(rel_file_path):
                continue

            _, ext = os.path.splitext(file)
            if ext not in ext_map:
                continue

            if is_binary_file(file_path):
                continue

            try:
                with open(file_path, "rb") as f:
                    content_bytes = f.read()

                # Safely decode string content, replacing invalid sequences
                content = content_bytes.decode("utf-8", errors="replace")

                # Skip completely blank files
                if not content.strip():
                    continue

                blob_sha = compute_git_blob_sha(content_bytes)
                repo_rel_path = rel_file_path.replace("\\", "/")

                candidates.append(
                    FileCandidate(
                        path=repo_rel_path,
                        language=ext_map[ext],
                        blob_sha=blob_sha,
                        content=content,
                    )
                )
            except Exception:
                continue

    return candidates
