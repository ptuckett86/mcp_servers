"""Review a PR for security issues, code violations, and logic gaps."""

from __future__ import annotations

import re
from typing import Any

from client.github import GitHubClient

Finding = dict[str, Any]

# (severity, category, pattern, title, detail) — applied against patch hunks / filenames.
SECURITY_RULES: list[tuple[str, str, re.Pattern[str], str, str]] = [
    (
        "critical",
        "security",
        re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        "Hardcoded secret-like value",
        "Credential appears embedded in source. Move to env/secret manager and rotate if committed.",
    ),
    (
        "critical",
        "security",
        re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
        "Possible AWS access key",
        "Looks like an AWS access key ID. Remove from the diff and rotate the key.",
    ),
    (
        "critical",
        "security",
        re.compile(r"(?i)(eval\s*\(|new Function\s*\(|exec\s*\(|os\.system\s*\()"),
        "Dynamic code execution",
        "eval/exec/system can enable RCE if fed untrusted input. Prefer safe parsers/APIs.",
    ),
    (
        "high",
        "security",
        re.compile(r"(?i)(innerHTML\s*=|dangerouslySetInnerHTML|document\.write\s*\()"),
        "Possible XSS sink",
        "DOM/HTML injection sink detected. Ensure content is sanitized or use safer APIs.",
    ),
    (
        "high",
        "security",
        re.compile(r"(?i)(SELECT|INSERT|UPDATE|DELETE).*\+|f[\"'].*\b(SELECT|INSERT|UPDATE|DELETE)\b|\.format\(.*\b(SELECT|INSERT)"),
        "Possible SQL injection pattern",
        "String-built SQL detected. Use parameterized queries / ORM bindings.",
    ),
    (
        "high",
        "security",
        re.compile(r"(?i)(verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*0|InsecureRequestWarning)"),
        "TLS verification disabled",
        "Disabling TLS verification enables MITM. Remove or tightly scope with documented risk.",
    ),
    (
        "high",
        "security",
        re.compile(r"(?i)(pickle\.loads?\s*\(|yaml\.load\s*\((?!.*Loader))"),
        "Insecure deserialization",
        "pickle/unsafe yaml.load can execute attacker-controlled objects. Use safe loaders.",
    ),
    (
        "medium",
        "security",
        re.compile(r"(?i)(md5|sha1)\s*\("),
        "Weak hash algorithm",
        "MD5/SHA1 are unsuitable for security-sensitive hashing. Prefer SHA-256+ or bcrypt/argon2.",
    ),
    (
        "medium",
        "security",
        re.compile(r"(?i)(cors\([^)]*origin\s*:\s*['\"]?\*|Access-Control-Allow-Origin:\s*\*)"),
        "Overly permissive CORS",
        "Wildcard CORS can expose authenticated APIs. Restrict origins deliberately.",
    ),
]

VIOLATION_RULES: list[tuple[str, str, re.Pattern[str], str, str]] = [
    (
        "high",
        "violation",
        re.compile(r"(?i)except\s*:"),
        "Bare except clause",
        "Bare except swallows unexpected errors. Catch specific exceptions.",
    ),
    (
        "medium",
        "violation",
        re.compile(r"(?i)#\s*(TODO|FIXME|HACK).*(security|auth|password|token)"),
        "Security-related TODO left in code",
        "Unresolved security TODO in the diff — track or resolve before merge.",
    ),
    (
        "medium",
        "violation",
        re.compile(r"(?i)console\.log\s*\(|print\s*\(.*password|print\s*\(.*token"),
        "Debug logging of sensitive context",
        "Debug prints may leak secrets or PII. Remove or redact before merge.",
    ),
    (
        "low",
        "violation",
        re.compile(r"(?i)debugger;|binding\.pry|pdb\.set_trace"),
        "Debugger statement",
        "Remove debugger breakpoints before merging.",
    ),
]

LOGIC_RULES: list[tuple[str, str, re.Pattern[str], str, str]] = [
    (
        "high",
        "logic",
        re.compile(r"(?i)^\+.*\b(pass|TODO|NotImplementedError|raise NotImplemented)\b"),
        "Stubbed implementation in added lines",
        "New code path appears unfinished. Confirm intentional or complete before merge.",
    ),
    (
        "medium",
        "logic",
        re.compile(r"(?i)^\+.*\bif\s*\([^)]*\)\s*\{\s*\}"),
        "Empty conditional body",
        "Empty if-block may indicate incomplete logic.",
    ),
    (
        "medium",
        "logic",
        re.compile(r"(?i)^\+.*\bcatch\s*\([^)]*\)\s*\{\s*\}"),
        "Empty catch block",
        "Swallowing errors hides failures. Log, rethrow, or handle explicitly.",
    ),
]


def _scan_patch(path: str, patch: str) -> list[Finding]:
    findings: list[Finding] = []
    added_lines = "\n".join(
        line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    # Also keep full patch for line-anchored logic rules
    for severity, category, pattern, title, detail in SECURITY_RULES + VIOLATION_RULES:
        if pattern.search(added_lines) or pattern.search(patch):
            findings.append(
                {
                    "severity": severity,
                    "category": category,
                    "title": title,
                    "detail": detail,
                    "path": path,
                }
            )
    for severity, category, pattern, title, detail in LOGIC_RULES:
        if pattern.search(patch):
            findings.append(
                {
                    "severity": severity,
                    "category": category,
                    "title": title,
                    "detail": detail,
                    "path": path,
                }
            )
    return findings


def _filename_findings(path: str) -> list[Finding]:
    findings: list[Finding] = []
    lower = path.lower()
    if any(lower.endswith(ext) for ext in (".pem", ".key", ".p12", ".pfx")):
        findings.append(
            {
                "severity": "critical",
                "category": "security",
                "title": "Private key / cert file in PR",
                "detail": "Binary/private material should not ship in git. Use a secret store.",
                "path": path,
            }
        )
    if any(name in lower for name in (".env", "credentials", "id_rsa", "secrets.")):
        findings.append(
            {
                "severity": "high",
                "category": "security",
                "title": "Sensitive config filename",
                "detail": "Filename suggests secrets. Confirm no credentials are committed.",
                "path": path,
            }
        )
    return findings


def _structural_findings(bundle: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    files = bundle.get("files") or []
    additions = bundle.get("additions") or 0
    deletions = bundle.get("deletions") or 0

    if additions + deletions > 1500:
        findings.append(
            {
                "severity": "medium",
                "category": "logic",
                "title": "Very large diff",
                "detail": (
                    f"PR touches ~{additions}+ / {deletions}- lines across {len(files)} files. "
                    "Large changes raise review risk for missed logic gaps — consider splitting."
                ),
                "path": None,
            }
        )

    code_files = [
        f
        for f in files
        if f.get("filename")
        and not f["filename"].endswith((".md", ".txt", ".lock", ".svg", ".png", ".jpg"))
    ]
    test_files = [
        f
        for f in code_files
        if re.search(r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec)\.", f["filename"], re.I)
    ]
    if code_files and additions > 80 and not test_files:
        findings.append(
            {
                "severity": "medium",
                "category": "logic",
                "title": "No test file changes detected",
                "detail": (
                    "Non-trivial code changes without accompanying tests. "
                    "Confirm coverage for new branches and failure modes."
                ),
                "path": None,
            }
        )

    auth_touched = any(
        re.search(r"(auth|session|permission|rbac|oauth|jwt)", f.get("filename", ""), re.I)
        for f in files
    )
    if auth_touched:
        findings.append(
            {
                "severity": "high",
                "category": "security",
                "title": "Auth-related paths changed",
                "detail": (
                    "Authentication/authorization files changed. Manually verify deny-by-default, "
                    "session invalidation, and privilege checks on every new endpoint."
                ),
                "path": None,
            }
        )
    return findings


def review_pull_request(pr_url: str) -> str:
    """Review a GitHub PR for security vulnerabilities, code violations, and logic gaps.

    Args:
        pr_url: GitHub pull request URL, or owner/repo#123.
    """
    try:
        client = GitHubClient()
        bundle = client.get_pr_bundle(pr_url)
    except Exception as exc:  # noqa: BLE001
        return f"Error fetching PR: {exc}"

    findings: list[Finding] = []
    findings.extend(_structural_findings(bundle))

    truncated_files = 0
    for file_info in bundle.get("files") or []:
        path = file_info.get("filename") or "unknown"
        findings.extend(_filename_findings(path))
        patch = file_info.get("patch")
        if not patch:
            # GitHub omits patches for binary/large files
            if file_info.get("status") in ("added", "modified", "renamed"):
                truncated_files += 1
            continue
        findings.extend(_scan_patch(path, patch))

    # Deduplicate by (path, title)
    seen: set[tuple[str | None, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.get("path"), finding["title"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    unique.sort(key=lambda f: (severity_order.get(f["severity"], 9), f["category"], f["title"]))

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in unique:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    lines = [
        f"# PR review — {bundle['owner']}/{bundle['repo']}#{bundle['number']}",
        "",
        f"**Title:** {bundle['title']}",
        f"**URL:** {bundle['url']}",
        f"**Author:** {bundle['user']} | **Base:** `{bundle['base']}` ← `{bundle['head']}`",
        f"**Diff:** +{bundle.get('additions')} / -{bundle.get('deletions')} "
        f"across {bundle.get('changed_files')} files",
        "",
        "## Summary",
        (
            f"Found **{len(unique)}** finding(s): "
            f"critical={counts['critical']}, high={counts['high']}, "
            f"medium={counts['medium']}, low={counts['low']}."
        ),
        "",
    ]

    if truncated_files:
        lines.append(
            f"_Note: {truncated_files} file(s) had no patch text (binary or too large); "
            "review those manually._"
        )
        lines.append("")

    if not unique:
        lines.append(
            "No automated findings. Still recommend a human pass for business-logic "
            "correctness and authorization edge cases."
        )
        return "\n".join(lines)

    lines.append("## Findings")
    lines.append("")
    for i, finding in enumerate(unique, start=1):
        loc = f" `{finding['path']}`" if finding.get("path") else ""
        lines.append(
            f"### {i}. [{finding['severity'].upper()}] [{finding['category']}] "
            f"{finding['title']}{loc}"
        )
        lines.append(finding["detail"])
        lines.append("")

    lines.extend(
        [
            "## Reviewer checklist (manual)",
            "- [ ] Untrusted input validated at boundaries",
            "- [ ] AuthZ checked on every new/changed endpoint",
            "- [ ] Error paths don't leak secrets",
            "- [ ] Happy path and failure path tests exist for new logic",
            "- [ ] Migrations / feature flags are backwards compatible",
            "",
            "## Agent follow-up",
            "Prioritize critical/high findings first. For each, propose a concrete patch "
            "and note residual risk if the issue cannot be fully confirmed from the diff alone.",
        ]
    )
    return "\n".join(lines)
