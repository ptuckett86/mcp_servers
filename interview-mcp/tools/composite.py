from __future__ import annotations

from tools.architecture import advise_architecture
from tools.pattern import detect_pattern
from tools.test_gen import generate_tests


def _is_backend_problem(problem: str) -> bool:
    text = problem.lower()
    backend_keywords = (
        "api",
        "rest",
        "fastapi",
        "database",
        "sql",
        "borrow",
        "library",
        "upload",
        "microservice",
        "architecture",
        "system design",
        "endpoint",
        "schema",
    )
    return any(kw in text for kw in backend_keywords)


def interview_analyze(problem: str) -> dict:
    """Composite interview analysis: pattern, tests, and architecture when relevant.

    One-shot entry point for starting an interview problem.
    """
    pattern = detect_pattern(problem)
    tests = generate_tests(problem)
    result: dict = {
        "problem_type": "mixed" if _is_backend_problem(problem) and pattern.get("matches") else (
            "backend" if _is_backend_problem(problem) else "dsa"
        ),
        "pattern_analysis": pattern,
        "test_plan": tests,
    }

    if _is_backend_problem(problem):
        arch = advise_architecture(problem)
        result["architecture"] = arch
        result["recommended_workflow"] = [
            "1. Clarify functional and non-functional requirements.",
            "2. Sketch data model and API contracts.",
            "3. Call generate_sql_schema and generate_fastapi_scaffold.",
            "4. Implement core paths with transactions where needed.",
            "5. Review with review_solution for race conditions.",
        ]
    else:
        result["recommended_workflow"] = [
            "1. Restate problem and confirm constraints.",
            "2. Identify pattern and write pseudocode.",
            "3. Implement clean solution with named variables.",
            "4. Run through generated test categories.",
            "5. State time/space complexity and optimizations.",
        ]

    primary = pattern.get("primary")
    if primary:
        result["headline"] = (
            f"Likely pattern: {primary['pattern']} — {primary['approach']}"
        )
    elif _is_backend_problem(problem):
        result["headline"] = "Backend/system design problem — start with requirements and data model."
    else:
        result["headline"] = "No strong DSA pattern — begin with brute force, then optimize."

    return result
