"""Tests for PR vs Jira ticket review."""

from __future__ import annotations

from tasks.pr_ticket_review import (
    _assess_requirement,
    _ticket_requirements,
    review_pull_request_against_ticket,
)


def test_ticket_requirements_prefers_bullets() -> None:
    bundle = {
        "summary": "Add export",
        "description": "- Export CSV for worklogs\n- Include user timezone",
    }
    reqs = _ticket_requirements(bundle)
    assert reqs == ["Export CSV for worklogs", "Include user timezone"]


def test_assess_requirement_detects_overlap(sample_pr_bundle) -> None:
    assessment = _assess_requirement(
        "Add a test for the null token case in session refresh",
        sample_pr_bundle,
    )
    assert assessment["status"] in {"likely_met", "partial"}
    assert assessment["matched_files"]


def test_review_pull_request_against_ticket(monkeypatch, sample_pr_bundle) -> None:
    ticket_bundle = {
        "key": "TT-8500",
        "url": "https://appfire.atlassian.net/browse/TT-8500",
        "summary": "Fix session refresh null token handling",
        "description": "- Add a test for the null token case.\n- Handle expired sessions safely.",
        "status": "In Progress",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["backend"],
        "extra_text_fields": {},
    }

    class FakeGitHub:
        def get_pr_bundle(self, pr_ref: str):
            return sample_pr_bundle

    class FakeJira:
        def get_ticket_bundle(self, ticket_ref: str):
            assert "TT-8500" in ticket_ref
            return ticket_bundle

    monkeypatch.setattr("tasks.pr_ticket_review.GitHubClient", FakeGitHub)
    monkeypatch.setattr("tasks.pr_ticket_review._load_jira_client", lambda: FakeJira())
    report = review_pull_request_against_ticket(
        "https://github.com/acme/widgets/pull/42",
        "https://appfire.atlassian.net/browse/TT-8500",
    )
    assert "PR vs ticket review" in report
    assert "TT-8500" in report
    assert "Requirements coverage" in report
    assert "Hardcoded secret-like value" in report or "Dynamic code execution" in report
    assert "Likely met" in report or "Partial" in report


def test_review_pull_request_against_ticket_error(monkeypatch) -> None:
    class Boom:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ValueError("GITHUB_TOKEN is not set")

    monkeypatch.setattr("tasks.pr_ticket_review.GitHubClient", Boom)
    report = review_pull_request_against_ticket(
        "https://github.com/acme/widgets/pull/1",
        "TT-1",
    )
    assert report.startswith("Error fetching PR or ticket:")
