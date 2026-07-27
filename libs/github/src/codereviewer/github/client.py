import hashlib
import hmac
import time
from typing import Any, Protocol

import httpx
import jwt


def verify_signature(secret: str, signature: str | None, body: bytes) -> bool:
    """Verify GitHub webhook payload signature against the shared secret."""
    if not signature:
        return False
    if signature.startswith("sha256="):
        signature = signature[7:]
    try:
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


class GitHubClient(Protocol):
    """Protocol for interacting with GitHub App APIs."""

    async def post_pr_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        comments: list[dict[str, Any]],
        body: str = "CodeReviewer.ai Review",
    ) -> int:
        """Post a pull request review with a cover summary and line comments."""
        ...


class MockGitHubClient(GitHubClient):
    """Mock GitHub client for offline testing."""

    def __init__(self) -> None:
        self.posted_reviews: list[dict[str, Any]] = []

    async def post_pr_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        comments: list[dict[str, Any]],
        body: str = "CodeReviewer.ai Review",
    ) -> int:
        """Record and mock the posting of a PR review."""
        self.posted_reviews.append(
            {
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "commit_sha": commit_sha,
                "comments": comments,
                "body": body,
            }
        )
        return len(self.posted_reviews)


class HttpGitHubClient(GitHubClient):
    """Production GitHub client using App token authentication."""

    def __init__(self, app_id: int, private_key: str, installation_id: int):
        self.app_id = app_id
        self.private_key = private_key
        self.installation_id = installation_id
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _generate_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - 60:
            return self._token

        jwt_token = self._generate_jwt()
        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self._token = data["token"]
            self._token_expires_at = now + 45 * 60
            return self._token

    async def post_pr_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        comments: list[dict[str, Any]],
        body: str = "CodeReviewer.ai Review",
    ) -> int:
        """Post the batched comments directly to the GitHub PR Reviews API."""
        token = await self._get_access_token()
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "commit_id": commit_sha,
            "event": "COMMENT",
            "body": body,
            "comments": comments,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return int(data["id"])
