"""Tests for PR security/code review heuristics."""

from __future__ import annotations

from tasks.pr_review import _filename_findings, _scan_patch, review_pull_request


def test_scan_patch_finds_hardcoded_secret() -> None:
    patch = (
        "@@ -1 +1,2 @@\n"
        " keep\n"
        "+api_key = 'sk_live_hardcoded_secret_value'\n"
    )
    findings = _scan_patch("config.py", patch)
    titles = {f["title"] for f in findings}
    assert "Hardcoded secret-like value" in titles


def test_scan_patch_finds_eval() -> None:
    patch = "@@ -1 +1,2 @@\n keep\n+result = eval(user_input)\n"
    findings = _scan_patch("evil.py", patch)
    assert any(f["title"] == "Dynamic code execution" for f in findings)


def test_filename_findings_for_env() -> None:
    findings = _filename_findings(".env.production")
    assert findings
    assert findings[0]["category"] == "security"


def test_review_pull_request(monkeypatch, sample_pr_bundle) -> None:
    class FakeClient:
        def get_pr_bundle(self, pr_ref: str):
            return sample_pr_bundle

    monkeypatch.setattr("tasks.pr_review.GitHubClient", FakeClient)
    report = review_pull_request("acme/widgets#42")
    assert "PR review" in report
    assert "Hardcoded secret-like value" in report or "Dynamic code execution" in report
    assert "auth/session.py" in report


def test_review_pull_request_clean_diff(monkeypatch) -> None:
    clean = {
        "owner": "acme",
        "repo": "widgets",
        "number": 1,
        "url": "https://github.com/acme/widgets/pull/1",
        "title": "Docs",
        "body": "",
        "state": "open",
        "draft": False,
        "user": "alice",
        "base": "main",
        "head": "docs",
        "additions": 2,
        "deletions": 0,
        "changed_files": 1,
        "issue_comments": [],
        "review_comments": [],
        "reviews": [],
        "files": [
            {
                "filename": "README.md",
                "status": "modified",
                "patch": "@@ -1 +1,2 @@\n # Hello\n+More docs\n",
            }
        ],
    }

    class FakeClient:
        def get_pr_bundle(self, pr_ref: str):
            return clean

    monkeypatch.setattr("tasks.pr_review.GitHubClient", FakeClient)
    report = review_pull_request("acme/widgets#1")
    assert "No automated findings" in report
