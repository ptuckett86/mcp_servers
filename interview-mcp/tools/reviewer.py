from __future__ import annotations

import re

from tools.pattern import detect_pattern

REVIEW_CHECKLIST = [
    "Correctness: Does the solution handle all stated requirements?",
    "Edge cases: empty input, single element, duplicates, negatives, max size?",
    "Time complexity: State and justify Big-O.",
    "Space complexity: Auxiliary structures accounted for?",
    "Off-by-one: Loop bounds, index ranges, inclusive vs exclusive?",
    "Mutability: Unintended input mutation?",
    "Naming and structure: Can you explain each block aloud?",
]


def _heuristic_flags(code: str, language: str, problem: str) -> list[dict]:
    flags: list[dict] = []
    text = code.lower()
    problem_lower = problem.lower()

    if re.search(r"for\s+\w+\s+in\s+.*:\s*\n\s*for\s+\w+\s+in", code):
        flags.append(
            {
                "severity": "warning",
                "issue": "Nested loops detected",
                "detail": "Verify O(n^2) is acceptable; consider hash map, sorting, or two pointers.",
            }
        )

    if "while" in text and "left" in text and "right" in text:
        flags.append(
            {
                "severity": "info",
                "issue": "Two-pointer pattern in use",
                "detail": "Confirm pointer movement covers all elements without skipping.",
            }
        )

    if language.lower() in ("python", "py") and re.search(r"except\s*:", code):
        flags.append(
            {
                "severity": "warning",
                "issue": "Bare except clause",
                "detail": "Catch specific exceptions in production code.",
            }
        )

    if any(kw in problem_lower for kw in ("borrow", "inventory", "transaction", "concurrent")):
        if "lock" not in text and "transaction" not in text and "for update" not in text:
            flags.append(
                {
                    "severity": "critical",
                    "issue": "Possible race condition",
                    "detail": "Inventory/borrow flows need transactions or row-level locking.",
                }
            )

    if re.search(r"select\s+\*\s+from", text) and "for" in text:
        flags.append(
            {
                "severity": "warning",
                "issue": "SELECT * inside loop",
                "detail": "N+1 query pattern; batch or join instead.",
            }
        )

    if "null" in text or "none" in text:
        if not re.search(r"(if\s+.*(is\s+none|==\s*none|!=\s*none|null)|\?\.|optional)", text):
            flags.append(
                {
                    "severity": "warning",
                    "issue": "Possible missing null checks",
                    "detail": "Validate inputs before dereferencing.",
                }
            )

    if len(code.strip()) < 20:
        flags.append(
            {
                "severity": "info",
                "issue": "Minimal code provided",
                "detail": "Review may be limited; paste full solution for deeper analysis.",
            }
        )

    return flags


def review_solution(problem: str, code: str, language: str = "python") -> dict:
    """Review a solution with a senior-engineer checklist and heuristic flags.

    Returns structured review items for correctness, complexity, and risks.
    """
    pattern_result = detect_pattern(problem)
    flags = _heuristic_flags(code, language, problem)

    return {
        "checklist": REVIEW_CHECKLIST,
        "detected_patterns": pattern_result.get("matches", []),
        "heuristic_flags": flags,
        "summary": (
            f"Review against {len(REVIEW_CHECKLIST)} criteria. "
            f"{len(flags)} heuristic flag(s) raised."
        ),
        "next_steps": [
            "Walk through each edge case manually.",
            "State time and space complexity aloud.",
            "Explain tradeoffs if asked to optimize further.",
        ],
    }
