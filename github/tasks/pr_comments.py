"""Read PR comments and instruct the agent to implement and stage the requested changes."""

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

NON_ACTIONABLE_PATTERNS = [
    r"^\s*lgtm\.?\s*$",
    r"^\s*looks good(?: to me)?\.?\s*$",
    r"^\s*approved\.?\s*$",
    r"^\s*ship it\.?\s*$",
    r"^\s*nice(?: work)?\.?\s*$",
    r"^\s*thanks?\.?\s*$",
    r"^\s*\+1\.?\s*$",
]


def _classify(body: str) -> list[str]:
    labels: list[str] = []
    text = body.lower()
    for pattern, label in ACTION_HINTS:
        if re.search(pattern, text):
            labels.append(label)
    return labels or ["general"]


def _is_actionable(body: str) -> bool:
    text = body.strip()
    if not text:
        return False
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in NON_ACTIONABLE_PATTERNS):
        return False
    return True


def _patch_for_path(files: list[dict[str, Any]], path: str | None) -> str | None:
    if not path:
        return None
    for file_info in files:
        if file_info.get("filename") == path:
            patch = (file_info.get("patch") or "").strip()
            return patch or None
    return None


def _build_change_instruction(
    body: str,
    labels: list[str],
    path: str | None,
    line: int | None,
    patch: str | None,
    *,
    dry_run: bool = False,
) -> str:
    """Concrete edit instruction for the agent to execute or preview."""
    location = f"`{path}`"
    if line:
        location += f" (around line {line})"
    elif path:
        location += " (exact line not provided — inspect nearby code)"

    primary = labels[0] if labels else "general"
    focus = {
        "bug": "Fix the reported defect with the smallest safe change.",
        "security": "Remediate the security concern; do not introduce new trust boundaries.",
        "performance": "Improve the hot path called out by the reviewer.",
        "testing": "Add or update tests to cover the scenario described.",
        "logic_gap": "Handle the missing edge case explicitly.",
        "refactor": "Refactor as requested without changing behavior.",
        "nit": "Apply the style or naming tweak requested.",
        "request": "Implement exactly what the reviewer asked for.",
        "general": "Implement the feedback if it is clear; otherwise ask one clarifying question.",
    }[primary]

    action = (
        "Describe the exact code change you would make, but do not edit files or run git."
        if dry_run
        else "Make the code change in the working tree now."
    )
    lines = [
        f"{'Would edit' if dry_run else 'Edit'} {location}. {focus}",
        f'Reviewer request: "{body}"',
    ]
    if patch:
        lines.extend(["", "Relevant diff hunk from the PR:", "```diff", patch, "```"])
    lines.append(action)
    return "\n".join(lines)


def _format_comment(
    comment: dict[str, Any],
    index: int,
    files: list[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    body = (comment.get("body") or "").strip()
    user = (comment.get("user") or {}).get("login") or "unknown"
    path = comment.get("path")
    line = comment.get("line") or comment.get("original_line")
    labels = _classify(body)
    patch = _patch_for_path(files, path)
    return {
        "id": f"unresolved-{index}",
        "kind": "unresolved_review",
        "author": user,
        "path": path,
        "line": line,
        "created_at": comment.get("created_at"),
        "body": body,
        "labels": labels,
        "actionable": _is_actionable(body),
        "change_instruction": _build_change_instruction(
            body,
            labels,
            path,
            line,
            patch,
            dry_run=dry_run,
        ),
        "html_url": comment.get("html_url"),
        "thread_id": comment.get("thread_id"),
    }


def _format_changed_files(files: list[dict[str, Any]]) -> list[str]:
    lines = ["## Files changed in this PR", ""]
    if not files:
        lines.append("(No file list returned by GitHub.)")
        return lines

    for file_info in files:
        filename = file_info.get("filename") or "unknown"
        status = file_info.get("status") or "changed"
        additions = file_info.get("additions")
        deletions = file_info.get("deletions")
        stats = ""
        if additions is not None and deletions is not None:
            stats = f" (+{additions}/-{deletions})"
        lines.append(f"- `{filename}` ({status}{stats})")
    lines.append("")
    return lines


def _likely_edit_paths(actionable_items: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for item in actionable_items:
        path = item.get("path")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def _staging_section(actionable_items: list[dict[str, Any]], *, dry_run: bool) -> list[str]:
    paths = _likely_edit_paths(actionable_items)
    if dry_run or not paths:
        return []

    quoted = " ".join(f'"{path}"' for path in paths)
    return [
        "## Mandatory staging (agent must run in the user's repo)",
        "",
        "The MCP server cannot access the local git repo. **You** (the Cursor agent) must "
        "stage edits after modifying files. Do not finish until this is done.",
        "",
        "Run these commands from the repository root after all edits:",
        "",
        "```bash",
        f"git add {quoted}",
        "git diff --staged --stat",
        "```",
        "",
        "If you edited additional files (for example tests), include them in `git add` too.",
        "Show the `git diff --staged --stat` output in your reply so the user can review "
        "before they commit manually.",
        "",
    ]


def _agent_workflow_lines(bundle: dict[str, Any], *, dry_run: bool) -> list[str]:
    head_branch = bundle.get("head") or "head branch"
    if dry_run:
        return [
            "## Required agent workflow (dry run)",
            "",
            "This is a **dry run**. Do not modify files, run tests, or execute any git commands.",
            "",
            "1. Read each actionable comment below and explain the concrete code change you "
            "would make to address it.",
            "2. Group related comments when they touch the same files or concern.",
            "3. Call out ambiguities, missing context, or comments that need clarification "
            "before coding.",
            "4. Finish with a concise plan the user can approve. Tell them to re-run "
            "`propose_pr_comment_solutions` with `dry_run=false` (or without saying "
            '"Dry run") to apply and stage the changes.',
            "",
        ]

    return [
        "## Required agent workflow",
        "",
        "**Important:** This MCP tool only returns instructions. Staging happens in the "
        "user's local repo when **you** run `git add` via the shell after editing files.",
        "",
        "You must implement the PR feedback in the user's local repository, then stage "
        "the edits for review.",
        "",
        "1. Ensure the working tree matches the PR branch "
        f"(`{head_branch}`) before editing.",
        "2. For each actionable comment below, modify the referenced files to satisfy "
        "the reviewer's request. Prefer minimal, focused diffs.",
        "3. Run relevant tests or linters when the change touches behavior.",
        "4. **Required:** run `git add` on every file you changed. Verify with "
        "`git diff --staged --stat` before responding.",
        "5. Do **not** run `git commit`, `git push`, or open a PR — the user will review "
        "staged changes first.",
        "6. Your reply is incomplete if files were edited but not staged.",
        "",
    ]


def _final_step_lines(*, dry_run: bool) -> list[str]:
    if dry_run:
        return [
            "## Final step",
            "",
            "Stop after presenting the plan. Wait for the user to approve before making "
            "any edits or staging files.",
        ]

    return [
        "## Final step",
        "",
        "Do not mark the task complete until staged changes exist. Run the `git add` "
        "commands above, paste `git diff --staged --stat` in your response, and remind "
        "the user they can review staged diffs in source control before committing manually.",
    ]


def propose_pr_comment_solutions(pr_url: str, dry_run: bool = False) -> str:
    """Implement unresolved PR review feedback in the local repo and stage changes for commit.

    Fetches unresolved inline review threads via GitHub GraphQL, ignores comments authored
    by the authenticated user, and returns instructions for the calling agent.

    When `dry_run` is false, the calling Cursor agent must:
    1. Edit files in the user's local workspace to address each comment
    2. Run `git add` on every modified file (the MCP server cannot run git locally)
    3. Show `git diff --staged --stat` and stop without committing

    Set `dry_run=true` (or say "Dry run" in your prompt) to preview the plan without
    editing files or running git.

    Args:
        pr_url: GitHub pull request URL, or owner/repo#123.
        dry_run: If true, only report what would change; do not edit or stage files.
    """
    try:
        client = GitHubClient()
        bundle = client.get_pr_review_work_bundle(pr_url)
    except Exception as exc:  # noqa: BLE001 - surface clean MCP errors
        return f"Error fetching PR: {exc}"

    files = bundle.get("files") or []
    reviewer_comments = bundle.get("reviewer_comments") or []
    items = [
        _format_comment(comment, index, files, dry_run=dry_run)
        for index, comment in enumerate(reviewer_comments, start=1)
    ]
    actionable_items = [item for item in items if item["actionable"]]

    title = (
        "# PR review changes — dry run (plan only)"
        if dry_run
        else "# PR review changes — implement and stage"
    )
    mode = "**Mode:** dry run — no file edits or git commands" if dry_run else "**Mode:** apply changes"

    lines = [
        title,
        "",
        mode,
        "",
        f"**Title:** {bundle['title']}",
        f"**URL:** {bundle['url']}",
        f"**Author:** {bundle['user']} | **State:** {bundle['state']}"
        + (" (draft)" if bundle.get("draft") else ""),
        f"**Base branch:** {bundle.get('base') or 'unknown'} | "
        f"**Head branch:** {bundle.get('head') or 'unknown'}",
        f"**Viewer:** @{bundle.get('viewer_login') or 'unknown'}",
        f"**Unresolved reviewer comments:** {len(items)} | **Actionable:** {len(actionable_items)}",
        "",
        "_Only unresolved inline review threads are included. Resolved threads, conversation "
        "comments, and your own comments are excluded._",
        "",
    ]
    lines.extend(_agent_workflow_lines(bundle, dry_run=dry_run))
    lines.extend(_format_changed_files(files))

    if bundle.get("body"):
        lines.extend(["## PR description", bundle["body"].strip(), ""])

    if not actionable_items:
        if not items:
            lines.append(
                "No unresolved reviewer comments found for you to address on this PR."
            )
        else:
            lines.append(
                "Unresolved reviewer comments were found, but none looked actionable "
                "(approvals/thanks only)."
            )
        return "\n".join(lines)

    lines.extend(["## Changes to implement", ""])
    for item in actionable_items:
        loc = ""
        if item.get("path"):
            loc = f" (`{item['path']}`"
            if item.get("line"):
                loc += f":{item['line']}"
            loc += ")"
        section = "**Planned change:**" if dry_run else "**Implement this change:**"
        lines.append(f"### {item['id']} — @{item['author']} [{item['kind']}]{loc}")
        lines.append(f"**Labels:** {', '.join(item['labels'])}")
        lines.append("")
        lines.append("**Reviewer comment:**")
        lines.append(item["body"])
        lines.append("")
        lines.append(section)
        lines.append(item["change_instruction"])
        lines.append("")

    skipped = len(items) - len(actionable_items)
    if skipped:
        lines.extend(
            [
                f"*{skipped} unresolved reviewer comment(s) skipped as non-actionable "
                "(approvals, thanks, etc.).*",
                "",
            ]
        )

    lines.extend(_staging_section(actionable_items, dry_run=dry_run))
    lines.extend(_final_step_lines(dry_run=dry_run))
    return "\n".join(lines)
