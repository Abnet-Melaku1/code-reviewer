import subprocess
from unittest.mock import MagicMock, patch

import pytest

from codereviewer.indexer.git import get_file_delta


def test_get_file_delta_success() -> None:
    mock_stdout = (
        "A\tsrc/new.py\nM\tsrc/modified.py\nD\tsrc/deleted.py\nR100\tsrc/old.py\tsrc/renamed.py\n"
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=mock_stdout)

        delta = get_file_delta("/path/to/repo", "sha_base", "sha_head")

        mock_run.assert_called_once_with(
            ["git", "diff", "--name-status", "sha_base..sha_head"],
            cwd="/path/to/repo",
            capture_output=True,
            text=True,
            check=True,
        )

        assert delta == {
            "src/new.py": "A",
            "src/modified.py": "M",
            "src/deleted.py": "D",
            "src/old.py": "D",
            "src/renamed.py": "A",
        }


def test_get_file_delta_empty() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        delta = get_file_delta("/path/to/repo", "sha_base", "sha_head")
        assert delta == {}


def test_get_file_delta_failure() -> None:
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
        with pytest.raises(subprocess.CalledProcessError):
            get_file_delta("/path/to/repo", "sha_base", "sha_head")
