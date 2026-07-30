"""Tests for trailing PR metrics."""

from __future__ import annotations

from datetime import datetime, timezone

from tasks.pr_metrics import (
    _owner_repo_from_search_item,
    compute_pr_metric_averages,
    trailing_month_pr_metrics,
)


def test_owner_repo_from_search_item() -> None:
    owner, repo, number = _owner_repo_from_search_item(
        {
            "number": 9,
            "repository_url": "https://api.github.com/repos/acme/widgets",
            "html_url": "https://github.com/acme/widgets/pull/9",
        }
    )
    assert (owner, repo, number) == ("acme", "widgets", 9)


def test_compute_pr_metric_averages() -> None:
    now = datetime(2026, 7, 30, tzinfo=timezone.utc)
    snapshots = [
        {
            # 2 days open, 4 commits → 2 commits/day; 6 comments
            "created_at": "2026-07-28T00:00:00Z",
            "closed_at": "2026-07-30T00:00:00Z",
            "merged_at": "2026-07-30T00:00:00Z",
            "state": "closed",
            "merged": True,
            "author_commit_count": 4,
            "comment_count": 6,
        },
        {
            # still open 1 day, 1 commit → 1 commit/day; 2 comments
            "created_at": "2026-07-29T00:00:00Z",
            "closed_at": None,
            "merged_at": None,
            "state": "open",
            "merged": False,
            "author_commit_count": 1,
            "comment_count": 2,
        },
    ]
    result = compute_pr_metric_averages(snapshots, now=now)
    assert result["pr_count"] == 2
    assert result["by_status"] == {"open": 1, "closed": 0, "merged": 1}
    assert abs(result["avg_author_commits_per_day"] - 1.5) < 1e-6
    assert abs(result["avg_comments"] - 4.0) < 1e-6
    assert abs(result["avg_time_open_days"] - 1.5) < 1e-6
    assert abs(result["avg_author_commits_per_pr"] - 2.5) < 1e-6


def test_compute_empty() -> None:
    result = compute_pr_metric_averages([])
    assert result["pr_count"] == 0
    assert result["avg_comments"] is None


def test_trailing_month_pr_metrics(monkeypatch) -> None:
    snapshots = [
        {
            "owner": "acme",
            "repo": "widgets",
            "number": 1,
            "url": "https://github.com/acme/widgets/pull/1",
            "title": "One",
            "state": "closed",
            "merged": True,
            "draft": False,
            "created_at": "2026-07-20T00:00:00Z",
            "closed_at": "2026-07-22T00:00:00Z",
            "merged_at": "2026-07-22T00:00:00Z",
            "author_commit_count": 2,
            "total_commit_count": 2,
            "comment_count": 3,
            "issue_comment_count": 1,
            "review_comment_count": 1,
            "review_summary_count": 1,
        }
    ]

    class FakeClient:
        def get_authenticated_user(self):
            return {"login": "alice"}

        def list_authored_prs_created_since(self, since_date: str, login: str | None = None):
            assert login == "alice"
            return [
                {
                    "number": 1,
                    "repository_url": "https://api.github.com/repos/acme/widgets",
                    "html_url": "https://github.com/acme/widgets/pull/1",
                }
            ]

        def get_pr_activity_snapshot(self, owner, repo, number, author_login):
            assert (owner, repo, number, author_login) == ("acme", "widgets", 1, "alice")
            return snapshots[0]

    monkeypatch.setattr("tasks.pr_metrics.GitHubClient", FakeClient)
    report = trailing_month_pr_metrics(days=30)
    assert "Trailing PR metrics — @alice" in report
    assert "Avg comments per PR" in report
    assert "acme/widgets#1" in report
    assert "PRs analyzed:** 1" in report


def test_trailing_month_pr_metrics_invalid_days() -> None:
    assert trailing_month_pr_metrics(days=0).startswith("Error:")
