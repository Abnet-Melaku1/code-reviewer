import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codereviewer.github.client import (
    HttpGitHubClient,
    MockGitHubClient,
    verify_signature,
)


def test_verify_signature() -> None:
    secret = "test_secret"
    body = b"hello world"
    sig = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()
    assert verify_signature(secret, sig, body) is True
    assert verify_signature(secret, "invalid", body) is False
    assert verify_signature(secret, None, body) is False


@pytest.mark.anyio
async def test_mock_github_client() -> None:
    client = MockGitHubClient()
    review_id = await client.post_pr_review(
        owner="owner",
        repo="repo",
        pr_number=5,
        commit_sha="sha",
        comments=[{"path": "f.py", "line": 1, "body": "nit"}],
    )
    assert review_id == 1
    assert len(client.posted_reviews) == 1
    assert client.posted_reviews[0]["pr_number"] == 5


@pytest.mark.anyio
@patch("httpx.AsyncClient.post")
async def test_http_github_client_token_minting(mock_post: AsyncMock) -> None:
    with patch("jwt.encode", return_value="mock_jwt") as mock_jwt_encode:
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "token_123"}
        mock_post.return_value = mock_response

        client = HttpGitHubClient(app_id=123, private_key="dummy_key", installation_id=456)
        token = await client._get_access_token()
        assert token == "token_123"
        mock_jwt_encode.assert_called_once()
        mock_post.assert_called_once_with(
            "https://api.github.com/app/installations/456/access_tokens",
            headers={
                "Authorization": "Bearer mock_jwt",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
