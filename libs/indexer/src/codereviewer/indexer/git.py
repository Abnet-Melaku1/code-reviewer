import subprocess


def get_file_delta(repo_path: str, base_sha: str, head_sha: str) -> dict[str, str]:
    """Run git diff --name-status to identify changes between two commits.

    Returns a dictionary mapping relative file paths to status characters:
      - 'A': Added
      - 'M': Modified
      - 'D': Deleted
    Renames are treated as a deletion of the old path and an addition of the new path.
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{base_sha}..{head_sha}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    delta = {}
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0]
            if status.startswith("R"):
                old_path = parts[1]
                new_path = parts[2] if len(parts) > 2 else parts[1]
                delta[old_path] = "D"
                delta[new_path] = "A"
            else:
                file_path = parts[1]
                char = status[0]
                if char in ("A", "M", "D"):
                    delta[file_path] = char
                else:
                    delta[file_path] = "M"
    return delta
