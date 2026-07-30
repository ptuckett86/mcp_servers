"""Shared fixtures for Jira MCP tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_ticket_bundle() -> dict:
    return {
        "key": "PROJ-99",
        "id": "10099",
        "url": "https://example.atlassian.net/browse/PROJ-99",
        "summary": "As a user I want password reset emails",
        "description": (
            "Acceptance criteria:\n"
            "- User can request a reset link\n"
            "- Link expires after 15 minutes\n"
            "The service must validate the token.\n"
            "Blocked by email provider decision?\n"
        ),
        "status": "In Progress",
        "issue_type": "Story",
        "priority": "High",
        "assignee": "Alice",
        "reporter": "Bob",
        "labels": ["auth"],
        "components": ["identity"],
        "parent": None,
        "created": "2026-01-01T00:00:00.000+0000",
        "updated": "2026-01-02T00:00:00.000+0000",
        "extra_text_fields": {},
        "comments": [
            {
                "id": "1",
                "author": "Carol",
                "created": "2026-01-01T12:00:00.000+0000",
                "updated": "2026-01-01T12:00:00.000+0000",
                "body": "We decided to go with SendGrid for email delivery.",
            },
            {
                "id": "2",
                "author": "Dave",
                "created": "2026-01-01T13:00:00.000+0000",
                "updated": "2026-01-01T13:00:00.000+0000",
                "body": "Blocked waiting on API keys. Next step: request staging credentials.",
            },
        ],
    }
