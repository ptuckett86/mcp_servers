"""Read Jira ticket comments and summarize the discussion."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from client.jira import JiraClient

THEME_PATTERNS = [
    (r"(?i)\b(block|blocked|waiting|depend)\b", "blockers"),
    (r"(?i)\b(decision|agreed|we'll|we will|go with|chose|decided)\b", "decisions"),
    (r"(?i)\b(question|clarif|\?)\b", "questions"),
    (r"(?i)\b(risk|concern|worry|issue)\b", "risks"),
    (r"(?i)\b(next step|action item|todo|please|need to)\b", "action_items"),
    (r"(?i)\b(deploy|release|ship|prod|staging)\b", "release"),
    (r"(?i)\b(test|qa|verify|repro)\b", "testing"),
]


def _themes_for(text: str) -> list[str]:
    themes = [label for pattern, label in THEME_PATTERNS if re.search(pattern, text)]
    return themes or ["general"]


def _shorten(text: str, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def summarize_ticket_comments(ticket: str) -> str:
    """Read comments on a Jira ticket and summarize the discussion.

    Args:
        ticket: Jira issue key (PROJ-123) or browse URL.
    """
    try:
        client = JiraClient()
        bundle = client.get_ticket_bundle(ticket)
    except Exception as exc:  # noqa: BLE001
        return f"Error fetching ticket: {exc}"

    comments: list[dict[str, Any]] = bundle.get("comments") or []
    lines = [
        f"# Ticket comment summary — {bundle['key']}",
        "",
        f"**URL:** {bundle['url']}",
        f"**Summary:** {bundle.get('summary')}",
        f"**Status:** {bundle.get('status')}",
        f"**Comment count:** {len(comments)}",
        "",
    ]

    if not comments:
        lines.append("No comments on this ticket.")
        return "\n".join(lines)

    theme_counter: Counter[str] = Counter()
    authors: Counter[str] = Counter()
    annotated: list[dict[str, Any]] = []

    for comment in comments:
        body = (comment.get("body") or "").strip()
        if not body:
            continue
        themes = _themes_for(body)
        for theme in themes:
            theme_counter[theme] += 1
        author = comment.get("author") or "unknown"
        authors[author] += 1
        annotated.append(
            {
                "author": author,
                "created": comment.get("created"),
                "themes": themes,
                "body": body,
                "excerpt": _shorten(body),
            }
        )

    lines.append("## Discussion overview")
    lines.append(
        f"{len(annotated)} non-empty comment(s) from "
        f"{len(authors)} participant(s): "
        + ", ".join(f"{name} ({count})" for name, count in authors.most_common())
    )
    lines.append("")
    if theme_counter:
        lines.append("**Themes mentioned:** " + ", ".join(
            f"{theme}×{count}" for theme, count in theme_counter.most_common()
        ))
        lines.append("")

    # Pull notable excerpts by theme priority
    priority = ["blockers", "decisions", "action_items", "questions", "risks", "release", "testing"]
    lines.append("## Key points by theme")
    lines.append("")
    for theme in priority:
        themed = [c for c in annotated if theme in c["themes"]]
        if not themed:
            continue
        lines.append(f"### {theme.replace('_', ' ').title()}")
        for item in themed[-5:]:  # latest-ish within theme
            when = (item.get("created") or "")[:19].replace("T", " ")
            lines.append(f"- **{item['author']}** ({when}): {item['excerpt']}")
        lines.append("")

    # Chronological condensed timeline (last 10)
    lines.append("## Recent timeline")
    lines.append("")
    for item in annotated[-10:]:
        when = (item.get("created") or "")[:19].replace("T", " ")
        theme_label = ", ".join(item["themes"])
        lines.append(f"- `{when}` **{item['author']}** [{theme_label}]: {item['excerpt']}")
    lines.append("")

    # Roll-up narrative
    decision_n = theme_counter.get("decisions", 0)
    blocker_n = theme_counter.get("blockers", 0)
    action_n = theme_counter.get("action_items", 0)
    narrative_bits = [
        f"Thread focuses on {theme_counter.most_common(1)[0][0].replace('_', ' ')}"
        if theme_counter
        else "Discussion is light on clear themes"
    ]
    if decision_n:
        narrative_bits.append(f"{decision_n} comment(s) signal decisions/agreements")
    if blocker_n:
        narrative_bits.append(f"{blocker_n} comment(s) mention blockers/dependencies")
    if action_n:
        narrative_bits.append(f"{action_n} comment(s) look like action items")

    lines.extend(
        [
            "## Executive summary",
            "; ".join(narrative_bits) + ".",
            "",
            "## Agent follow-up",
            "Surface unresolved questions and blockers first, then list agreed decisions "
            "and remaining action items as a checklist for whoever picks up the ticket.",
        ]
    )
    return "\n".join(lines)
