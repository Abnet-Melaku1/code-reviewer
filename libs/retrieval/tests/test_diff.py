from codereviewer.retrieval.diff import parse_diff_hunks
from codereviewer.schemas.enums import DiffSide


def test_parse_diff_hunks_basic() -> None:
    diff = (
        "diff --git a/src/main.py b/src/main.py\n"
        "index 12345..67890 100644\n"
        "--- a/src/main.py\n"
        "+++ b/src/main.py\n"
        "@@ -10,6 +10,7 @@ def hello():\n"
        "     print('first line')\n"
        "-    print('old')\n"
        "+    print('new')\n"
        "     print('last line')\n"
    )
    hunks = parse_diff_hunks(diff)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.file_path == "src/main.py"
    assert hunk.start_line == 10
    assert hunk.end_line == 16
    assert hunk.side == DiffSide.right
    assert "print('new')" in hunk.content
