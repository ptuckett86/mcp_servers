"""Shared fixtures for GitHub MCP tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_pr_bundle() -> dict:
    return {
        "owner": "acme",
        "repo": "widgets",
        "number": 42,
        "url": "https://github.com/acme/widgets/pull/42",
        "title": "Fix login timeout",
        "body": "Handles expired sessions.",
        "state": "open",
        "draft": False,
        "user": "alice",
        "base": "main",
        "head": "fix/login",
        "additions": 120,
        "deletions": 10,
        "changed_files": 3,
        "issue_comments": [
            {
                "body": "This looks like a bug in session refresh.",
                "user": {"login": "bob"},
                "created_at": "2026-01-01T00:00:00Z",
                "html_url": "https://github.com/acme/widgets/pull/42#issuecomment-1",
            }
        ],
        "review_comments": [
            {
                "body": "Please add a test for the null token case.",
                "user": {"login": "carol"},
                "path": "auth/session.py",
                "line": 88,
                "created_at": "2026-01-01T01:00:00Z",
                "html_url": "https://github.com/acme/widgets/pull/42#discussion_r1",
            }
        ],
        "reviews": [
            {
                "body": "LGTM after the security fix.",
                "user": {"login": "dave"},
                "submitted_at": "2026-01-01T02:00:00Z",
                "html_url": "https://github.com/acme/widgets/pull/42#pullrequestreview-1",
            }
        ],
        "files": [
            {
                "filename": "auth/session.py",
                "status": "modified",
                "patch": (
                    "@@ -1,3 +1,4 @@\n"
                    " def refresh(token):\n"
                    "+    api_key = 'sk_live_hardcoded_secret_value'\n"
                    "+    eval(user_input)\n"
                    "     return token\n"
                ),
            },
            {
                "filename": "auth/session_test.py",
                "status": "added",
                "patch": "@@ -0,0 +1,2 @@\n+def test_refresh():\n+    assert True\n",
            },
        ],
    }
