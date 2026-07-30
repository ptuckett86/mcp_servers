"""Tests for Jira ticket review."""

from __future__ import annotations

from tasks.ticket_review import _extract_bullets, _infer_intent, review_ticket


def test_extract_bullets() -> None:
    text = "- first item\n* second item\n1. third item\nplain"
    assert _extract_bullets(text) == ["first item", "second item", "third item"]


def test_infer_intent_user_story() -> None:
    result = _infer_intent(
        "As a user I want notifications",
        "Acceptance criteria: given when then",
        "Story",
    )
    assert "user_story" in result["signals"]
    assert "user-facing" in result["intent"].lower() or "capability" in result["intent"].lower()


def test_review_ticket(monkeypatch, sample_ticket_bundle) -> None:
    class FakeClient:
        def get_ticket_bundle(self, ticket: str):
            assert "PROJ-99" in ticket.upper() or ticket.endswith("PROJ-99")
            return sample_ticket_bundle

    monkeypatch.setattr("tasks.ticket_review.JiraClient", FakeClient)
    report = review_ticket("PROJ-99")
    assert "Ticket review — PROJ-99" in report
    assert "password reset" in report.lower() or "Concrete asks" in report
    assert "User can request a reset link" in report


def test_review_ticket_error(monkeypatch) -> None:
    class Boom:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ValueError("Missing Jira config")

    monkeypatch.setattr("tasks.ticket_review.JiraClient", Boom)
    report = review_ticket("PROJ-1")
    assert report.startswith("Error fetching ticket:")
