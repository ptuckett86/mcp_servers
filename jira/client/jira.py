"""Jira Cloud/Server API client authenticated with a personal API token."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

TICKET_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
BROWSE_RE = re.compile(r"/browse/([A-Z][A-Z0-9]+-\d+)", re.IGNORECASE)


class JiraClient:
    """Thin Jira REST client scoped to the authenticated user's token."""

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        token: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
        self.email = email or os.environ.get("JIRA_EMAIL", "")
        self.token = token or os.environ.get("JIRA_API_TOKEN", "")

        missing = [
            name
            for name, value in (
                ("JIRA_BASE_URL", self.base_url),
                ("JIRA_EMAIL", self.email),
                ("JIRA_API_TOKEN", self.token),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing Jira config: {', '.join(missing)}. "
                "Add them to mcp_servers/.env or your environment."
            )

        self._auth = (self.email, self.token)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "jira-mcp-server",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        with httpx.Client(timeout=60.0, headers=self._headers, auth=self._auth) as client:
            response = client.request(method, url, **kwargs)
            if response.status_code == 404:
                raise ValueError(f"Jira resource not found: {path}")
            if response.status_code == 401:
                raise ValueError(
                    "Jira authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN."
                )
            if response.status_code == 403:
                raise ValueError(f"Jira access denied (403): {response.text[:300]}")
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return response.json()

    @staticmethod
    def parse_ticket_key(ticket_ref: str) -> str:
        """Parse a ticket key from PROJ-123 or a browse URL."""
        text = ticket_ref.strip()
        browse = BROWSE_RE.search(text)
        if browse:
            return browse.group(1).upper()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9]+-\d+", text):
            return text.upper()
        match = TICKET_KEY_RE.search(text)
        if match:
            return match.group(1).upper()
        raise ValueError(
            "Unrecognized ticket reference. Use a key like PROJ-123 or a Jira browse URL."
        )

    @staticmethod
    def _adf_to_text(node: Any) -> str:
        """Flatten Atlassian Document Format (or plain string) to text."""
        if node is None:
            return ""
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "\n".join(JiraClient._adf_to_text(item) for item in node)
        if not isinstance(node, dict):
            return str(node)

        node_type = node.get("type")
        text = node.get("text", "")
        content = node.get("content", [])

        if node_type == "text":
            return text
        if node_type == "hardBreak":
            return "\n"
        if node_type == "mention":
            attrs = node.get("attrs") or {}
            return f"@{attrs.get('text') or attrs.get('id') or 'user'}"
        if node_type == "emoji":
            return (node.get("attrs") or {}).get("shortName", "")
        if node_type == "inlineCard":
            return (node.get("attrs") or {}).get("url", "")
        if node_type in ("paragraph", "heading", "blockquote", "listItem", "panel"):
            inner = "".join(JiraClient._adf_to_text(c) for c in content)
            return inner + "\n"
        if node_type in ("bulletList", "orderedList", "doc", "table", "tableRow", "tableCell"):
            return "".join(JiraClient._adf_to_text(c) for c in content)
        if node_type == "codeBlock":
            code = "".join(JiraClient._adf_to_text(c) for c in content)
            return f"```\n{code}\n```\n"
        if content:
            return "".join(JiraClient._adf_to_text(c) for c in content)
        return text

    def get_myself(self) -> dict[str, Any]:
        return self._request("GET", "/rest/api/3/myself")

    def get_issue(self, ticket_ref: str, expand: str = "renderedFields,names") -> dict[str, Any]:
        key = self.parse_ticket_key(ticket_ref)
        return self._request(
            "GET",
            f"/rest/api/3/issue/{key}",
            params={
                "expand": expand,
                "fields": "*all",
            },
        )

    def get_comments(self, ticket_ref: str) -> list[dict[str, Any]]:
        key = self.parse_ticket_key(ticket_ref)
        comments: list[dict[str, Any]] = []
        start_at = 0
        while True:
            page = self._request(
                "GET",
                f"/rest/api/3/issue/{key}/comment",
                params={"startAt": start_at, "maxResults": 100, "orderBy": "created"},
            ) or {}
            batch = page.get("comments") or []
            comments.extend(batch)
            start_at += len(batch)
            if start_at >= page.get("total", 0) or not batch:
                break
        return comments

    def get_ticket_bundle(self, ticket_ref: str) -> dict[str, Any]:
        """Fetch issue fields plus all comments, normalized to plain text."""
        issue = self.get_issue(ticket_ref)
        fields = issue.get("fields") or {}
        comments_raw = self.get_comments(ticket_ref)

        description = fields.get("description")
        description_text = self._adf_to_text(description).strip()
        rendered = (issue.get("renderedFields") or {}).get("description")
        if rendered and isinstance(rendered, str) and not description_text:
            description_text = re.sub(r"<[^>]+>", " ", rendered)
            description_text = re.sub(r"\s+", " ", description_text).strip()

        normalized_comments = []
        for comment in comments_raw:
            body = self._adf_to_text(comment.get("body")).strip()
            author = (comment.get("author") or {}).get("displayName") or (
                comment.get("author") or {}
            ).get("emailAddress")
            normalized_comments.append(
                {
                    "id": comment.get("id"),
                    "author": author,
                    "created": comment.get("created"),
                    "updated": comment.get("updated"),
                    "body": body,
                }
            )

        extra_text_fields: dict[str, str] = {}
        for field_key, value in fields.items():
            if not field_key.startswith("customfield_") or not value:
                continue
            if isinstance(value, (int, float, bool)):
                continue
            text = self._adf_to_text(value).strip()
            if text and len(text) > 20:
                extra_text_fields[field_key] = text

        return {
            "key": issue.get("key"),
            "id": issue.get("id"),
            "url": f"{self.base_url}/browse/{issue.get('key')}",
            "summary": fields.get("summary") or "",
            "description": description_text,
            "status": ((fields.get("status") or {}).get("name")),
            "issue_type": ((fields.get("issuetype") or {}).get("name")),
            "priority": ((fields.get("priority") or {}) or {}).get("name"),
            "assignee": ((fields.get("assignee") or {}) or {}).get("displayName"),
            "reporter": ((fields.get("reporter") or {}) or {}).get("displayName"),
            "labels": fields.get("labels") or [],
            "components": [c.get("name") for c in (fields.get("components") or []) if c.get("name")],
            "parent": ((fields.get("parent") or {}) or {}).get("key"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "extra_text_fields": extra_text_fields,
            "comments": normalized_comments,
        }
