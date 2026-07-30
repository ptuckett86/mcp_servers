"""Read a Jira ticket and describe what it is asking for."""

from __future__ import annotations

import re
from typing import Any

from client.jira import JiraClient

REQUIREMENT_PATTERNS = [
    (r"(?i)\bas a\b.+\bi (want|need|can)\b", "user_story"),
    (r"(?i)\bacceptance criteria\b|\bac:\b|\bgiven\b.+\bwhen\b.+\bthen\b", "acceptance"),
    (r"(?i)\b(must|shall|should|needs? to|required to)\b", "requirement"),
    (r"(?i)\b(bug|defect|broken|incorrect|fails?|error)\b", "bug"),
    (r"(?i)\b(spike|investigate|research|explore|poc)\b", "spike"),
    (r"(?i)\b(refactor|cleanup|tech debt|chore)\b", "chore"),
]


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
    return [p.strip() for p in parts if p and len(p.strip()) > 20]


def _infer_intent(summary: str, description: str, issue_type: str | None) -> dict[str, Any]:
    blob = f"{summary}\n{description}"
    signals: list[str] = []
    for pattern, label in REQUIREMENT_PATTERNS:
        if re.search(pattern, blob):
            signals.append(label)

    itype = (issue_type or "").lower()
    if "bug" in itype and "bug" not in signals:
        signals.append("bug")
    if "story" in itype and "user_story" not in signals:
        signals.append("user_story")
    if "task" in itype and "requirement" not in signals:
        signals.append("requirement")

    if "bug" in signals:
        intent = "Fix a defect and restore expected behavior."
    elif "spike" in signals:
        intent = "Investigate and report findings; implementation may be out of scope."
    elif "chore" in signals:
        intent = "Perform a maintenance/refactor change without altering product behavior."
    elif "user_story" in signals:
        intent = "Deliver a user-facing capability described by the story."
    else:
        intent = "Implement the requested change described in the ticket."

    return {"signals": signals or ["general"], "intent": intent}


def review_ticket(ticket: str) -> str:
    """Read a Jira ticket and describe what it appears to be asking for.

    Args:
        ticket: Jira issue key (PROJ-123) or browse URL.
    """
    try:
        client = JiraClient()
        bundle = client.get_ticket_bundle(ticket)
    except Exception as exc:  # noqa: BLE001
        return f"Error fetching ticket: {exc}"

    summary = bundle.get("summary") or ""
    description = bundle.get("description") or ""
    inference = _infer_intent(summary, description, bundle.get("issue_type"))
    bullets = _extract_bullets(description)
    sentences = _split_sentences(description)

    # Prefer explicit bullets as asks; otherwise use leading sentences.
    asks = bullets[:12] if bullets else sentences[:6]
    if not asks and summary:
        asks = [summary]

    open_questions: list[str] = []
    for pattern, label in (
        (r"\?\s*$", "unanswered question in description"),
        (r"(?i)\b(tbd|to be determined|not sure|unclear|need clarification)\b", "ambiguity marker"),
        (r"(?i)\b(depends on|blocked by|waiting on)\b", "dependency"),
    ):
        if re.search(pattern, description, re.M):
            open_questions.append(label)

    lines = [
        f"# Ticket review — {bundle['key']}",
        "",
        f"**URL:** {bundle['url']}",
        f"**Type:** {bundle.get('issue_type')} | **Status:** {bundle.get('status')} "
        f"| **Priority:** {bundle.get('priority')}",
        f"**Assignee:** {bundle.get('assignee') or 'Unassigned'} | "
        f"**Reporter:** {bundle.get('reporter') or 'Unknown'}",
        f"**Labels:** {', '.join(bundle.get('labels') or []) or '(none)'}",
        f"**Components:** {', '.join(bundle.get('components') or []) or '(none)'}",
        "",
        "## Summary",
        summary or "(no summary)",
        "",
        "## What this ticket is asking for",
        inference["intent"],
        "",
        f"**Signals detected:** {', '.join(inference['signals'])}",
        "",
        "### Concrete asks",
    ]

    if asks:
        for ask in asks:
            lines.append(f"- {ask}")
    else:
        lines.append("- (insufficient detail in ticket body)")

    lines.extend(["", "### Description (source)", description or "(empty description)", ""])

    extras = bundle.get("extra_text_fields") or {}
    if extras:
        lines.append("### Additional text fields")
        for key, value in list(extras.items())[:8]:
            preview = value if len(value) <= 500 else value[:500] + "…"
            lines.append(f"**{key}:**")
            lines.append(preview)
            lines.append("")

    if open_questions:
        lines.append("### Ambiguities / risks")
        for q in open_questions:
            lines.append(f"- {q}")
        lines.append("")

    comment_count = len(bundle.get("comments") or [])
    lines.extend(
        [
            f"**Comments on ticket:** {comment_count} "
            "(use `summarize_ticket_comments` for discussion context).",
            "",
            "## Agent interpretation guide",
            "Restate the goal in one sentence, list acceptance criteria as testable bullets, "
            "call out missing info before coding, and map work to concrete code/files when possible.",
        ]
    )
    return "\n".join(lines)
