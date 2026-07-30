"""Tests for Jira ticket comment summaries."""

from __future__ import annotations

from tasks.ticket_comments import _shorten, _themes_for, summarize_ticket_comments


def test_themes_for_blockers_and_decisions() -> None:
    themes = _themes_for("We decided to go with option A but are blocked waiting on keys")
    assert "decisions" in themes
    assert "blockers" in themes


def test_shorten_truncates() -> None:
    text = "x" * 400
    shortened = _shorten(text, limit=50)
    assert len(shortened) == 50
    assert shortened.endswith("…")


def test_summarize_ticket_comments(monkeypatch, sample_ticket_bundle) -> None:
    class FakeClient:
        def get_ticket_bundle(self, ticket: str):
            return sample_ticket_bundle

    monkeypatch.setattr("tasks.ticket_comments.JiraClient", FakeClient)
    report = summarize_ticket_comments("https://example.atlassian.net/browse/PROJ-99")
    assert "Ticket comment summary — PROJ-99" in report
    assert "SendGrid" in report
    assert "blockers" in report.lower() or "Blocked" in report
    assert "Executive summary" in report


def test_summarize_no_comments(monkeypatch, sample_ticket_bundle) -> None:
    bundle = dict(sample_ticket_bundle)
    bundle["comments"] = []

    class FakeClient:
        def get_ticket_bundle(self, ticket: str):
            return bundle

    monkeypatch.setattr("tasks.ticket_comments.JiraClient", FakeClient)
    report = summarize_ticket_comments("PROJ-99")
    assert "No comments on this ticket." in report
