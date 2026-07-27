import re

from codereviewer.schemas.enums import DiffSide
from codereviewer.schemas.models import DiffHunk


def parse_diff_hunks(diff_content: str) -> list[DiffHunk]:
    """Parse a unified diff string into a list of DiffHunk domain models."""
    hunks = []
    current_file = None

    # Matches @@ -start,len +start,len @@
    hunk_header_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    lines = diff_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("+++ b/"):
            # Target file path
            current_file = line[6:].strip()
            i += 1
            continue
        elif line.startswith("+++ /dev/null"):
            # File deleted, no target side file to review
            current_file = None
            i += 1
            continue
        elif line.startswith("@@"):
            if not current_file:
                i += 1
                continue
            match = hunk_header_re.match(line)
            if match:
                start_line = int(match.group(1))
                length = int(match.group(2)) if match.group(2) else 1

                # Gather hunk lines
                hunk_lines = [line]
                i += 1
                while (
                    i < len(lines)
                    and not lines[i].startswith("diff --git ")
                    and not lines[i].startswith("@@")
                ):
                    hunk_lines.append(lines[i])
                    i += 1

                hunks.append(
                    DiffHunk(
                        file_path=current_file,
                        content="\n".join(hunk_lines),
                        start_line=start_line,
                        end_line=start_line + max(0, length - 1),
                        side=DiffSide.right,
                    )
                )
                continue
        i += 1
    return hunks
