"""GitHub API client authenticated with a personal access token."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

PR_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)
PR_SHORT_RE = re.compile(
    r"^(?P<owner>[^/\s]+)/(?P<repo>[^#\s]+)#(?P<number>\d+)$",
)


class GitHubClient:
    """Thin GitHub REST client scoped to the authenticated user's token."""

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        if not self.token:
            raise ValueError(
                "GITHUB_TOKEN is not set. Add it to mcp_servers/.env or your environment."
            )
        self.base_url = (base_url or os.environ.get("GITHUB_API_BASE", "https://api.github.com")).rstrip(
            "/"
        )
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-mcp-server",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        with httpx.Client(timeout=60.0, headers=self._headers) as client:
            response = client.request(method, url, **kwargs)
            if response.status_code == 404:
                raise ValueError(f"GitHub resource not found: {path}")
            if response.status_code == 401:
                raise ValueError("GitHub authentication failed. Check GITHUB_TOKEN.")
            if response.status_code == 403:
                raise ValueError(
                    f"GitHub access denied (403): {response.text[:300]}. "
                    "Token may lack required scopes (repo, pull_requests)."
                )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    @staticmethod
    def parse_pr_ref(pr_ref: str) -> tuple[str, str, int]:
        """Parse a PR URL or owner/repo#123 into (owner, repo, number)."""
        text = pr_ref.strip()
        match = PR_URL_RE.search(text) or PR_SHORT_RE.match(text)
        if not match:
            raise ValueError(
                "Unrecognized PR reference. Use a GitHub PR URL "
                "(https://github.com/owner/repo/pull/123) or owner/repo#123."
            )
        return match.group("owner"), match.group("repo"), int(match.group("number"))

    def get_authenticated_user(self) -> dict[str, Any]:
        return self._request("GET", "/user")

    def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")

    def get_issue_comments(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        """Conversation comments on the PR (issue comments)."""
        return self._request("GET", f"/repos/{owner}/{repo}/issues/{number}/comments") or []

    def get_review_comments(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        """Inline review comments on the PR diff."""
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}/comments") or []

    def get_reviews(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}/reviews") or []

    def get_files(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{number}/files",
                params={"per_page": 100, "page": page},
            ) or []
            files.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return files

    def get_pr_bundle(self, pr_ref: str) -> dict[str, Any]:
        """Fetch PR metadata, comments, reviews, and changed files."""
        owner, repo, number = self.parse_pr_ref(pr_ref)
        pr = self.get_pull_request(owner, repo, number)
        return {
            "owner": owner,
            "repo": repo,
            "number": number,
            "url": pr.get("html_url") or f"https://github.com/{owner}/{repo}/pull/{number}",
            "title": pr.get("title", ""),
            "body": pr.get("body") or "",
            "state": pr.get("state"),
            "draft": pr.get("draft", False),
            "user": (pr.get("user") or {}).get("login"),
            "base": (pr.get("base") or {}).get("ref"),
            "head": (pr.get("head") or {}).get("ref"),
            "additions": pr.get("additions"),
            "deletions": pr.get("deletions"),
            "changed_files": pr.get("changed_files"),
            "issue_comments": self.get_issue_comments(owner, repo, number),
            "review_comments": self.get_review_comments(owner, repo, number),
            "reviews": self.get_reviews(owner, repo, number),
            "files": self.get_files(owner, repo, number),
        }
