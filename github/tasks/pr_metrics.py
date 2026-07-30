"""Trailing-window averages across the authenticated user's PRs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any
from urllib.parse import urlparse

from client.github import GitHubClient


def _parse_github_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub returns ISO-8601 with Z
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _days_open(created_at: datetime, ended_at: datetime) -> float:
    """Open duration in days (fractional), minimum one hour so tiny PRs aren't infinite rates."""
    seconds = max((ended_at - created_at).total_seconds(), 3600.0)
    return seconds / 86400.0


def _owner_repo_from_search_item(item: dict[str, Any]) -> tuple[str, str, int]:
    """Extract owner/repo/number from a search issue payload."""
    number = int(item["number"])
    repo_url = item.get("repository_url") or ""
    # https://api.github.com/repos/owner/repo
    parts = urlparse(repo_url).path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "repos":
        return parts[1], parts[2], number
    html = item.get("html_url") or ""
    # https://github.com/owner/repo/pull/123
    html_parts = urlparse(html).path.strip("/").split("/")
    if len(html_parts) >= 4:
        return html_parts[0], html_parts[1], number
    raise ValueError(f"Could not parse repo from search item: {item.get('html_url')}")


def _status_bucket(snapshot: dict[str, Any]) -> str:
    if snapshot.get("merged"):
        return "merged"
    if snapshot.get("state") == "closed":
        return "closed"
    return "open"


def compute_pr_metric_averages(snapshots: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any]:
    """Compute averages from per-PR activity snapshots."""
    now = now or datetime.now(timezone.utc)
    if not snapshots:
        return {
            "pr_count": 0,
            "avg_author_commits_per_day": None,
            "avg_comments": None,
            "avg_time_open_days": None,
            "avg_author_commits_per_pr": None,
            "by_status": {"open": 0, "closed": 0, "merged": 0},
        }

    commits_per_day: list[float] = []
    comments: list[float] = []
    time_open_days: list[float] = []
    commits_per_pr: list[float] = []
    by_status = {"open": 0, "closed": 0, "merged": 0}

    for snap in snapshots:
        created = _parse_github_dt(snap.get("created_at"))
        if not created:
            continue
        ended = (
            _parse_github_dt(snap.get("merged_at"))
            or _parse_github_dt(snap.get("closed_at"))
            or now
        )
        open_days = _days_open(created, ended)
        author_commits = float(snap.get("author_commit_count") or 0)
        commits_per_pr.append(author_commits)
        commits_per_day.append(author_commits / open_days)
        comments.append(float(snap.get("comment_count") or 0))
        time_open_days.append(open_days)
        by_status[_status_bucket(snap)] += 1

    return {
        "pr_count": len(commits_per_pr),
        "avg_author_commits_per_day": mean(commits_per_day) if commits_per_day else None,
        "avg_comments": mean(comments) if comments else None,
        "avg_time_open_days": mean(time_open_days) if time_open_days else None,
        "avg_author_commits_per_pr": mean(commits_per_pr) if commits_per_pr else None,
        "by_status": by_status,
    }


def trailing_month_pr_metrics(days: int = 30) -> str:
    """Average PR metrics for the authenticated user's PRs over a trailing window.

    Includes PRs you authored that were created in the last `days` days (open, closed,
    or merged). Reports:
    - avg author commits/day (per-PR commits÷days-open, then averaged)
    - avg comments per PR (conversation + inline review + review summaries)
    - avg time open in days (created → merged/closed/now)

    Args:
        days: Trailing window length in days (default 30).
    """
    if days < 1 or days > 365:
        return "Error: days must be between 1 and 365."

    try:
        client = GitHubClient()
        user = client.get_authenticated_user()
        login = user.get("login")
        if not login:
            return "Error: authenticated user has no login."

        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).date().isoformat()
        hits = client.list_authored_prs_created_since(since, login=login)

        snapshots: list[dict[str, Any]] = []
        errors: list[str] = []
        for item in hits:
            try:
                owner, repo, number = _owner_repo_from_search_item(item)
                snapshots.append(
                    client.get_pr_activity_snapshot(owner, repo, number, author_login=login)
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{item.get('html_url')}: {exc}")

        averages = compute_pr_metric_averages(snapshots, now=now)
    except Exception as exc:  # noqa: BLE001
        return f"Error fetching PR metrics: {exc}"

    def fmt(value: float | None, digits: int = 2) -> str:
        if value is None:
            return "n/a"
        return f"{value:.{digits}f}"

    lines = [
        f"# Trailing PR metrics — @{login}",
        "",
        f"**Window:** last {days} days (PRs you authored, created on/after `{since}`)",
        f"**PRs analyzed:** {averages['pr_count']}"
        f" (open={averages['by_status']['open']},"
        f" merged={averages['by_status']['merged']},"
        f" closed={averages['by_status']['closed']})",
        "",
        "## Averages",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Avg commits/day (your commits per PR ÷ days open, then averaged) | "
        f"{fmt(averages['avg_author_commits_per_day'])} |",
        f"| Avg comments per PR | {fmt(averages['avg_comments'])} |",
        f"| Avg time open (days) | {fmt(averages['avg_time_open_days'])} |",
        f"| Avg your commits per PR | {fmt(averages['avg_author_commits_per_pr'])} |",
        "",
        "### Notes",
        "- **Commits/day:** for each PR, count commits authored/committed by you, "
        "divide by that PR's open duration (created → merged/closed, or now if still open), "
        "then average across PRs.",
        "- **Comments:** conversation comments + inline review comments + non-empty review summaries.",
        "- **Time open:** includes open, closed, and merged PRs in the window.",
    ]

    if snapshots:
        lines.extend(["", "## Per-PR detail", ""])
        for snap in sorted(snapshots, key=lambda s: s.get("created_at") or "", reverse=True):
            created = _parse_github_dt(snap.get("created_at"))
            ended = (
                _parse_github_dt(snap.get("merged_at"))
                or _parse_github_dt(snap.get("closed_at"))
                or now
            )
            open_days = _days_open(created, ended) if created else 0.0
            cpd = (snap["author_commit_count"] / open_days) if open_days else 0.0
            lines.append(
                f"- [{snap['owner']}/{snap['repo']}#{snap['number']}]({snap['url']}) "
                f"`{_status_bucket(snap)}` — "
                f"your commits={snap['author_commit_count']}, "
                f"comments={snap['comment_count']}, "
                f"open={open_days:.2f}d, "
                f"commits/day={cpd:.2f}"
            )

    if errors:
        lines.extend(["", "## Fetch errors", ""])
        for err in errors[:20]:
            lines.append(f"- {err}")

    return "\n".join(lines)
