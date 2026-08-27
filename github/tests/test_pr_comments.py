"""Tests for PR comment implementation instructions."""

from __future__ import annotations

from tasks.pr_comments import (
    _build_change_instruction,
    _classify,
    _is_actionable,
    propose_pr_comment_solutions,
)


def test_classify_bug_and_security() -> None:
    labels = _classify("This security bug allows XSS injection")
    assert "bug" in labels
    assert "security" in labels


def test_is_actionable_skips_lgtm() -> None:
    assert not _is_actionable("LGTM")
    assert _is_actionable("Please add a null check")


def test_build_change_instruction_includes_path_and_patch() -> None:
    text = _build_change_instruction(
        "please fix",
        ["request"],
        "app.py",
        12,
        "@@ -1 +1 @@\n-old\n+new",
    )
    assert "`app.py`" in text
    assert "around line 12" in text
    assert "Make the code change in the working tree now." in text
    assert "```diff" in text


def test_propose_pr_comment_solutions(monkeypatch, sample_pr_review_bundle) -> None:
    class FakeClient:
        def get_pr_review_work_bundle(self, pr_ref: str):
            assert "42" in pr_ref
            return sample_pr_review_bundle

    monkeypatch.setattr("tasks.pr_comments.GitHubClient", FakeClient)
    report = propose_pr_comment_solutions("https://github.com/acme/widgets/pull/42")
    assert "PR review changes — implement and stage" in report
    assert "Fix login timeout" in report
    assert "Required agent workflow" in report
    assert "Only unresolved inline review threads" in report
    assert "git add" in report
    assert "Do **not** run `git commit`" in report
    assert "Mandatory staging" in report
    assert 'git add "auth/session.py"' in report
    assert "Implement this change" in report
    assert "session.py" in report
    assert "@carol" in report or "carol" in report
    assert "bob" not in report.split("## Changes to implement")[-1]
    assert "alice" not in report.split("## Changes to implement")[-1]


def test_propose_pr_comment_solutions_dry_run(monkeypatch, sample_pr_review_bundle) -> None:
    class FakeClient:
        def get_pr_review_work_bundle(self, pr_ref: str):
            return sample_pr_review_bundle

    monkeypatch.setattr("tasks.pr_comments.GitHubClient", FakeClient)
    report = propose_pr_comment_solutions(
        "https://github.com/acme/widgets/pull/42",
        dry_run=True,
    )
    assert "dry run (plan only)" in report
    assert "Do not modify files" in report
    assert "Planned change:" in report
    assert "Would edit" in report
    assert "git add" not in report
    assert "Mandatory staging" not in report


def test_propose_pr_comment_solutions_error(monkeypatch) -> None:
    class Boom:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            raise ValueError("GITHUB_TOKEN is not set")

    monkeypatch.setattr("tasks.pr_comments.GitHubClient", Boom)
    report = propose_pr_comment_solutions("https://github.com/acme/widgets/pull/1")
    assert report.startswith("Error fetching PR:")
