"""Read PR comments and propose concrete solutions for each request."""

from __future__ import annotations

import re
from typing import Any

from client.github import GitHubClient

# Patterns that suggest actionable feedback vs pure chatter.
ACTION_HINTS = [
    (r"\b(please|could you|can you|should|must|need to|needs? to)\b", "request"),
    (r"\b(bug|broken|fail|error|incorrect|wrong|regression)\b", "bug"),
    (r"\b(security|vuln|xss|injection|auth|secret|credential)\b", "security"),
    (r"\b(nit|nitpick|style|naming|typo|optional)\b", "nit"),
    (r"\b(perf|performance|slow|optimiz|memory|leak)\b", "performance"),
    (r"\b(test|coverage|assert|flake)\b", "testing"),
    (r"\b(missing|gap|handle|edge case|null|undefined)\b", "logic_gap"),
    (r"\b(refactor|extract|duplicat|dry)\b", "refactor"),
]


def _classify(body: str) -> list[str]:
    labels: list[str] = []
    text = body.lower()
    for pattern, label in ACTION_HINTS:
        if re.search(pattern, text):
            labels.append(label)
    return labels or ["general"]


def _propose_solution(body: str, labels: list[str], path: str | None) -> str:
    """Heuristic proposed fix framing for the agent/user to act on."""
    location = f" in `{path}`" if path else ""
    primary = labels[0] if labels else "general"

    templates = {
        "bug": (
            f"Treat this as a defect report{location}. Reproduce from the comment, "
            "add/adjust a failing test that captures the reported behavior, then fix the "
            "implementation until the test passes. Confirm related edge cases in the same path."
        ),
        "security": (
            f"Treat this as a security finding{location}. Verify whether untrusted input "
            "reaches a sink (SQL, HTML, shell, authz). Prefer parameterized queries, "
            "output encoding, least-privilege checks, and secret removal from source/history."
        ),
        "performance": (
            f"Profile or reason about the hot path{location}. Look for N+1 queries, "
            "unbounded loops, missing indexes, and unnecessary allocations. Propose a "
            "measured change with expected complexity impact."
        ),
        "testing": (
            f"Expand or fix tests{location} to cover the scenario described. Prefer "
            "focused unit/integration tests over broad rewrites; assert both success and "
            "failure paths called out by the reviewer."
        ),
        "logic_gap": (
            f"Add explicit handling{location} for the missing case (null/empty/error/"
            "boundary). Document the chosen behavior and guard with a regression test."
        ),
        "refactor": (
            f"Extract or deduplicate as requested{location} without changing behavior. "
            "Keep the diff small; preserve public APIs unless the comment asks otherwise."
        ),
        "nit": (
            f"Apply the style/naming tweak{location} if cheap; otherwise reply noting "
            "you'll defer to a follow-up if it risks scope creep."
        ),
        "request": (
            f"Implement the requested change{location}. Restate acceptance criteria from "
            "the comment, make the minimal diff that satisfies it, and note residual risks."
        ),
        "general": (
            f"Acknowledge the feedback{location}. If actionable, outline a concrete code "
            "change; if unclear, ask one clarifying question before changing behavior."
        ),
    }
    return templates.get(primary, templates["general"])


def _format_comment(kind: str, comment: dict[str, Any], index: int) -> dict[str, Any]:
    body = (comment.get("body") or "").strip()
    user = (comment.get("user") or {}).get("login") or "unknown"
    path = comment.get("path")
    line = comment.get("line") or comment.get("original_line")
    labels = _classify(body)
    return {
        "id": f"{kind}-{index}",
        "kind": kind,
        "author": user,
        "path": path,
        "line": line,
        "created_at": comment.get("created_at"),
        "body": body,
        "labels": labels,
        "proposed_solution": _propose_solution(body, labels, path),
        "html_url": comment.get("html_url"),
    }


def propose_pr_comment_solutions(pr_url: str) -> str:
    """Read all comments on a GitHub PR and propose a solution for each actionable item.

    Args:
        pr_url: GitHub pull request URL, or owner/repo#123.
    """
    try:
        client = GitHubClient()
        bundle = client.get_pr_bundle(pr_url)
    except Exception as exc:  # noqa: BLE001 - surface clean MCP errors
        return f"Error fetching PR: {exc}"

    items: list[dict[str, Any]] = []
    for i, c in enumerate(bundle["issue_comments"], start=1):
        items.append(_format_comment("conversation", c, i))
    for i, c in enumerate(bundle["review_comments"], start=1):
        items.append(_format_comment("inline_review", c, i))

    for i, review in enumerate(bundle["reviews"], start=1):
        body = (review.get("body") or "").strip()
        if not body:
            continue
        items.append(
            _format_comment(
                "review_summary",
                {
                    "body": body,
                    "user": review.get("user"),
                    "created_at": review.get("submitted_at"),
                    "html_url": review.get("html_url"),
                },
                i,
            )
        )

    lines = [
        f"# PR comment solutions — {bundle['owner']}/{bundle['repo']}#{bundle['number']}",
        "",
        f"**Title:** {bundle['title']}",
        f"**URL:** {bundle['url']}",
        f"**Author:** {bundle['user']} | **State:** {bundle['state']}"
        + (" (draft)" if bundle.get("draft") else ""),
        f"**Comments analyzed:** {len(items)}",
        "",
    ]

    if bundle.get("body"):
        lines.extend(["## PR description", bundle["body"].strip(), ""])

    if not items:
        lines.append("No comments or review notes found on this PR.")
        return "\n".join(lines)

    lines.append("## Proposed solutions by comment")
    lines.append("")
    for item in items:
        loc = ""
        if item.get("path"):
            loc = f" (`{item['path']}`"
            if item.get("line"):
                loc += f":{item['line']}"
            loc += ")"
        lines.append(f"### {item['id']} — @{item['author']} [{item['kind']}]{loc}")
        lines.append(f"**Labels:** {', '.join(item['labels'])}")
        lines.append("")
        lines.append("**Comment:**")
        lines.append(item["body"])
        lines.append("")
        lines.append("**Proposed solution:**")
        lines.append(item["proposed_solution"])
        lines.append("")

    lines.extend(
        [
            "## Agent follow-up",
            "Use the proposed solutions above as a starting plan. Prefer minimal diffs, "
            "group related comments into one commit when safe, and call out anything that "
            "needs product clarification before coding.",
        ]
    )
    return "\n".join(lines)
