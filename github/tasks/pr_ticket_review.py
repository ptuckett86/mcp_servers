"""Review a PR against a Jira ticket for security issues and requirements coverage."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from client.github import GitHubClient
from tasks.pr_review import analyze_pull_request, _format_pr_findings_report

_STOPWORDS = {
    "about",
    "after",
    "also",
    "been",
    "before",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "just",
    "like",
    "make",
    "more",
    "must",
    "need",
    "only",
    "should",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "through",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}


def _load_jira_client():
    try:
        from jira_client import JiraClient
    except ImportError:
        jira_root = Path(__file__).resolve().parents[2] / "jira"
        if str(jira_root) not in sys.path:
            sys.path.insert(0, str(jira_root))
        from client.jira import JiraClient  # type: ignore[import-not-found]
    return JiraClient


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^([-*$•]|\d+[.)])\s+", stripped):
            cleaned = re.sub(r"^([-*$•]|\d+[.)])\s+", "", stripped).strip()
            if cleaned:
                bullets.append(cleaned)
    return bullets


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if part and len(part.strip()) > 20]


def _ticket_requirements(ticket_bundle: dict[str, Any]) -> list[str]:
    description = ticket_bundle.get("description") or ""
    summary = ticket_bundle.get("summary") or ""
    bullets = _extract_bullets(description)
    if bullets:
        return bullets[:20]
    sentences = _split_sentences(description)
    if sentences:
        return sentences[:12]
    if summary:
        return [summary]
    return []


def _pr_search_corpus(bundle: dict[str, Any]) -> str:
    chunks = [
        bundle.get("title") or "",
        bundle.get("body") or "",
    ]
    for file_info in bundle.get("files") or []:
        chunks.append(file_info.get("filename") or "")
        chunks.append(file_info.get("patch") or "")
    return "\n".join(chunks).lower()


def _keywords(text: str) -> set[str]:
    words = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)}
    return {word for word in words if word not in _STOPWORDS and not word.isdigit()}


def _assess_requirement(requirement: str, pr_bundle: dict[str, Any]) -> dict[str, Any]:
    corpus = _pr_search_corpus(pr_bundle)
    requirement_keywords = _keywords(requirement)
    if not requirement_keywords:
        return {
            "status": "manual_check",
            "label": "Manual check",
            "evidence": ["Requirement text is too short for automated keyword matching."],
        }

    matched_files: list[str] = []
    evidence: list[str] = []
    for file_info in pr_bundle.get("files") or []:
        path = file_info.get("filename") or ""
        patch = file_info.get("patch") or ""
        haystack = f"{path}\n{patch}".lower()
        hits = sorted(word for word in requirement_keywords if word in haystack)
        if hits:
            matched_files.append(path)
            evidence.append(f"`{path}` mentions: {', '.join(hits[:6])}")

    overlap = sum(1 for word in requirement_keywords if word in corpus)
    ratio = overlap / len(requirement_keywords)

    if ratio >= 0.45 or (matched_files and ratio >= 0.25):
        status = "likely_met"
        label = "Likely met"
    elif matched_files or ratio >= 0.15:
        status = "partial"
        label = "Partial / unclear"
    else:
        status = "missing"
        label = "No evidence in PR diff"

    if not evidence:
        evidence.append("No changed files clearly reference this requirement's keywords.")

    return {
        "status": status,
        "label": label,
        "evidence": evidence[:4],
        "matched_files": matched_files[:6],
        "keyword_overlap": round(ratio, 2),
    }


def _ticket_context_lines(ticket_bundle: dict[str, Any]) -> list[str]:
    lines = [
        f"**Ticket:** [{ticket_bundle['key']}]({ticket_bundle['url']})",
        f"**Summary:** {ticket_bundle.get('summary') or '(none)'}",
        f"**Type:** {ticket_bundle.get('issue_type')} | **Status:** {ticket_bundle.get('status')} "
        f"| **Priority:** {ticket_bundle.get('priority')}",
        f"**Labels:** {', '.join(ticket_bundle.get('labels') or []) or '(none)'}",
        "",
        "### Ticket description",
        ticket_bundle.get("description") or "(empty description)",
        "",
    ]
    extras = ticket_bundle.get("extra_text_fields") or {}
    if extras:
        lines.append("### Additional ticket fields")
        for key, value in list(extras.items())[:5]:
            preview = value if len(value) <= 400 else value[:400] + "…"
            lines.append(f"**{key}:** {preview}")
        lines.append("")
    return lines


def _requirements_coverage_lines(
    requirements: list[str],
    pr_bundle: dict[str, Any],
    ticket_key: str,
) -> list[str]:
    lines = [
        "## Requirements coverage (ticket vs PR)",
        "",
        f"Comparing PR changes against **{ticket_key}**. This is heuristic — verify "
        "edge cases and acceptance criteria manually.",
        "",
    ]

    ticket_key_lower = ticket_key.lower()
    pr_text = f"{pr_bundle.get('title', '')}\n{pr_bundle.get('body', '')}".lower()
    if ticket_key_lower in pr_text:
        lines.append(f"_Ticket key `{ticket_key}` appears in the PR title/body._")
        lines.append("")

    if not requirements:
        lines.append(
            "No concrete requirements could be extracted from the ticket. Review the ticket "
            "description manually against the PR."
        )
        return lines

    status_counts = {"likely_met": 0, "partial": 0, "missing": 0, "manual_check": 0}
    for index, requirement in enumerate(requirements, start=1):
        assessment = _assess_requirement(requirement, pr_bundle)
        status_counts[assessment["status"]] = status_counts.get(assessment["status"], 0) + 1
        lines.append(f"### {index}. {assessment['label']}")
        lines.append(f"- **Requirement:** {requirement}")
        lines.append(f"- **Keyword overlap:** {assessment['keyword_overlap']}")
        for item in assessment["evidence"]:
            lines.append(f"- **Evidence:** {item}")
        lines.append("")

    lines.extend(
        [
            "### Coverage summary",
            f"- Likely met: {status_counts['likely_met']}",
            f"- Partial / unclear: {status_counts['partial']}",
            f"- No evidence in diff: {status_counts['missing']}",
            f"- Manual check: {status_counts['manual_check']}",
            "",
        ]
    )
    return lines


def review_pull_request_against_ticket(pr_url: str, ticket: str) -> str:
    """Review a PR for risks and compare the implementation against a Jira ticket.

    Scans the PR diff for security vulnerabilities, sensitive data, code-quality issues,
    and logic gaps, then compares changed files against ticket requirements to flag
    missing or partial coverage.

    Args:
        pr_url: GitHub pull request URL, or owner/repo#123.
        ticket: Jira issue key (TT-8500) or browse URL.
    """
    try:
        github = GitHubClient()
        pr_bundle = github.get_pr_bundle(pr_url)
        jira = _load_jira_client()
        ticket_bundle = jira.get_ticket_bundle(ticket)
    except Exception as exc:  # noqa: BLE001
        return f"Error fetching PR or ticket: {exc}"

    findings, truncated_files = analyze_pull_request(pr_bundle)
    requirements = _ticket_requirements(ticket_bundle)
    ticket_key = ticket_bundle.get("key") or ticket

    lines = [
        f"# PR vs ticket review — {pr_bundle['owner']}/{pr_bundle['repo']}#{pr_bundle['number']}",
        "",
        f"**PR:** [{pr_bundle['title']}]({pr_bundle['url']})",
        f"**Ticket:** [{ticket_key}]({ticket_bundle['url']})",
        "",
        "## Ticket context",
        "",
    ]
    lines.extend(_ticket_context_lines(ticket_bundle))
    lines.extend(
        _format_pr_findings_report(
            pr_bundle,
            findings,
            truncated_files=truncated_files,
            heading="## PR code review",
        )
    )
    lines.extend(_requirements_coverage_lines(requirements, pr_bundle, ticket_key))
    lines.extend(
        [
            "## Gaps and loopholes to verify manually",
            "",
            "- Business rules that are not spelled out in the ticket but implied by the domain",
            "- Authorization paths on new/changed endpoints (deny-by-default)",
            "- Regression risk for unrelated features touched in the same files",
            "- Error handling, retries, and partial-failure behavior",
            "- Missing tests for acceptance criteria marked partial or missing above",
            "",
            "## Agent follow-up",
            "",
            "1. Address critical/high security findings before merge.",
            "2. For each partial/missing requirement, either implement the gap or explain why "
            "the ticket is already satisfied.",
            "3. Call out any ticket acceptance criteria that cannot be confirmed from the diff alone.",
        ]
    )
    return "\n".join(lines)
