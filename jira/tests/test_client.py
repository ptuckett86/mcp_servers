"""Tests for the Jira API client."""

from __future__ import annotations

import httpx
import pytest

from client.jira import JiraClient


def test_parse_ticket_key() -> None:
    assert JiraClient.parse_ticket_key("PROJ-123") == "PROJ-123"


def test_parse_ticket_browse_url() -> None:
    assert (
        JiraClient.parse_ticket_key("https://acme.atlassian.net/browse/proj-42")
        == "PROJ-42"
    )


def test_parse_ticket_invalid() -> None:
    with pytest.raises(ValueError, match="Unrecognized ticket reference"):
        JiraClient.parse_ticket_key("nope")


def test_requires_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="Missing Jira config"):
        JiraClient()


def test_adf_to_text_flattens_doc() -> None:
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Hello "},
                    {"type": "mention", "attrs": {"text": "alice"}},
                ],
            },
            {
                "type": "codeBlock",
                "content": [{"type": "text", "text": "print(1)"}],
            },
        ],
    }
    text = JiraClient._adf_to_text(adf)
    assert "Hello" in text
    assert "@alice" in text
    assert "print(1)" in text


def test_get_ticket_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    client = JiraClient(
        base_url="https://example.atlassian.net",
        email="you@example.com",
        token="token",
    )

    monkeypatch.setattr(
        client,
        "get_issue",
        lambda ticket_ref, expand="renderedFields,names": {
            "key": "PROJ-1",
            "id": "1",
            "fields": {
                "summary": "Do the thing",
                "description": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Please implement X"}],
                        }
                    ],
                },
                "status": {"name": "To Do"},
                "issuetype": {"name": "Task"},
                "priority": {"name": "Medium"},
                "assignee": {"displayName": "Alice"},
                "reporter": {"displayName": "Bob"},
                "labels": ["backend"],
                "components": [{"name": "api"}],
                "parent": None,
                "created": "2026-01-01T00:00:00.000+0000",
                "updated": "2026-01-01T00:00:00.000+0000",
            },
            "renderedFields": {},
        },
    )
    monkeypatch.setattr(
        client,
        "get_comments",
        lambda ticket_ref: [
            {
                "id": "9",
                "author": {"displayName": "Carol"},
                "created": "2026-01-01T01:00:00.000+0000",
                "updated": "2026-01-01T01:00:00.000+0000",
                "body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Looks good"}]}]},
            }
        ],
    )

    bundle = client.get_ticket_bundle("PROJ-1")
    assert bundle["key"] == "PROJ-1"
    assert bundle["summary"] == "Do the thing"
    assert "Please implement X" in bundle["description"]
    assert bundle["comments"][0]["author"] == "Carol"
    assert "Looks good" in bundle["comments"][0]["body"]


def test_request_maps_401(monkeypatch: pytest.MonkeyPatch) -> None:
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
    client = JiraClient(
        base_url="https://example.atlassian.net",
        email="you@example.com",
        token="bad",
    )
    with pytest.raises(ValueError, match="authentication failed"):
        client._request("GET", "/rest/api/3/myself")
