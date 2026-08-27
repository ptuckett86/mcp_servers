"""Tests for the GitHub API client."""

from __future__ import annotations

import httpx
import pytest

from client.github import GitHubClient


def test_parse_pr_url() -> None:
    assert GitHubClient.parse_pr_ref("https://github.com/acme/widgets/pull/42") == (
        "acme",
        "widgets",
        42,
    )


def test_parse_pr_short_ref() -> None:
    assert GitHubClient.parse_pr_ref("acme/widgets#7") == ("acme", "widgets", 7)


def test_parse_pr_invalid() -> None:
    with pytest.raises(ValueError, match="Unrecognized PR reference"):
        GitHubClient.parse_pr_ref("not-a-pr")


def test_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        GitHubClient()


def test_get_pr_bundle_assembles_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GitHubClient(token="test-token")

    monkeypatch.setattr(
        client,
        "get_pull_request",
        lambda owner, repo, number: {
            "html_url": "https://github.com/acme/widgets/pull/42",
            "title": "Hello",
            "body": "Body",
            "state": "open",
            "draft": False,
            "user": {"login": "alice"},
            "base": {"ref": "main"},
            "head": {"ref": "feature"},
            "additions": 1,
            "deletions": 0,
            "changed_files": 1,
        },
    )
    monkeypatch.setattr(client, "get_issue_comments", lambda *a: [{"id": 1, "body": "hi"}])
    monkeypatch.setattr(client, "get_review_comments", lambda *a: [])
    monkeypatch.setattr(client, "get_reviews", lambda *a: [])
    monkeypatch.setattr(client, "get_files", lambda *a: [{"filename": "a.py", "patch": "+x"}])

    bundle = client.get_pr_bundle("https://github.com/acme/widgets/pull/42")
    assert bundle["owner"] == "acme"
    assert bundle["number"] == 42
    assert bundle["title"] == "Hello"
    assert bundle["issue_comments"][0]["body"] == "hi"
    assert bundle["files"][0]["filename"] == "a.py"


def test_request_maps_auth_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    real_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(401, text="nope"))

    class _Client:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            self._inner = real_client(transport=transport)

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:  # noqa: ANN002
            self._inner.close()

        def request(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return self._inner.request(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _Client)
    client = GitHubClient(token="bad")
    with pytest.raises(ValueError, match="authentication failed"):
        client._request("GET", "/user")


def test_get_unresolved_reviewer_comments_filters_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    client = GitHubClient(token="test-token")

    monkeypatch.setattr(
        client,
        "get_authenticated_user",
        lambda: {"login": "alice"},
    )
    monkeypatch.setattr(
        client,
        "graphql",
        lambda query, variables=None: {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "PRRT_resolved",
                                "isResolved": True,
                                "path": "old.py",
                                "line": 1,
                                "comments": {
                                    "nodes": [
                                        {
                                            "body": "Fix this",
                                            "createdAt": "2026-01-01T00:00:00Z",
                                            "url": "https://example.com/1",
                                            "author": {"login": "bob"},
                                        }
                                    ]
                                },
                            },
                            {
                                "id": "PRRT_open",
                                "isResolved": False,
                                "path": "auth/session.py",
                                "line": 88,
                                "comments": {
                                    "nodes": [
                                        {
                                            "body": "Please add a test.",
                                            "createdAt": "2026-01-01T01:00:00Z",
                                            "url": "https://example.com/2",
                                            "author": {"login": "carol"},
                                        },
                                        {
                                            "body": "Will do.",
                                            "createdAt": "2026-01-01T02:00:00Z",
                                            "url": "https://example.com/3",
                                            "author": {"login": "alice"},
                                        },
                                    ]
                                },
                            },
                        ],
                    }
                }
            }
        },
    )

    comments = client.get_unresolved_reviewer_comments("acme", "widgets", 42)
    assert len(comments) == 1
    assert comments[0]["user"]["login"] == "carol"
    assert comments[0]["path"] == "auth/session.py"
    assert comments[0]["thread_id"] == "PRRT_open"
