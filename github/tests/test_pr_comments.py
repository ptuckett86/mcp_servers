"""Tests for PR comment solution proposals."""

from __future__ import annotations

from tasks.pr_comments import _classify, _propose_solution, propose_pr_comment_solutions


def test_classify_bug_and_security() -> None:
    labels = _classify("This security bug allows XSS injection")
    assert "bug" in labels
    assert "security" in labels


def test_propose_solution_includes_path() -> None:
    text = _propose_solution("please fix", ["request"], "app.py")
    assert "`app.py`" in text
    assert "Implement the requested change" in text


def test_propose_pr_comment_solutions(monkeypatch, sample_pr_bundle) -> None:
    class FakeClient:
        def get_pr_bundle(self, pr_ref: str):
            assert "42" in pr_ref
            return sample_pr_bundle

    monkeypatch.setattr("tasks.pr_comments.GitHubClient", FakeClient)
    report = propose_pr_comment_solutions("https://github.com/acme/widgets/pull/42")
    assert "PR comment solutions" in report
    assert "Fix login timeout" in report
    assert "Proposed solution" in report
    assert "session.py" in report
    assert "@bob" in report or "bob" in report


def test_propose_pr_comment_solutions_error(monkeypatch) -> None:
    class Boom:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ValueError("GITHUB_TOKEN is not set")

    monkeypatch.setattr("tasks.pr_comments.GitHubClient", Boom)
    report = propose_pr_comment_solutions("https://github.com/acme/widgets/pull/1")
    assert report.startswith("Error fetching PR:")
