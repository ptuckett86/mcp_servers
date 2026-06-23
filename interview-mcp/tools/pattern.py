from __future__ import annotations

from tools.knowledge import load_dsa_patterns


def _score_pattern(problem: str, pattern: dict) -> tuple[int, list[str]]:
    text = problem.lower()
    matched: list[str] = []
    score = 0
    for signal in pattern.get("signals", []):
        if signal.lower() in text:
            matched.append(signal)
            score += 1
    return score, matched


def detect_pattern(problem: str) -> dict:
    """Detect likely DSA patterns from a problem statement.

    Scores the problem text against known pattern signals and returns
    the top matches with approach, complexity, and pitfalls.
    """
    if not problem.strip():
        return {
            "matches": [],
            "recommendation": "Provide a problem statement to analyze.",
        }

    scored: list[tuple[int, dict, list[str]]] = []
    for pattern in load_dsa_patterns():
        score, matched = _score_pattern(problem, pattern)
        if score > 0:
            scored.append((score, pattern, matched))

    scored.sort(key=lambda x: (-x[0], x[1]["name"]))

    matches = []
    for score, pattern, matched in scored[:2]:
        matches.append(
            {
                "pattern": pattern["name"],
                "confidence": score,
                "matched_signals": matched,
                "why": f"Matched signals: {', '.join(matched)}",
                "approach": pattern["approach"],
                "complexity": pattern["complexity"],
                "pitfalls": pattern["pitfalls"],
                "example_problems": pattern.get("example_problems", []),
            }
        )

    if not matches:
        return {
            "matches": [],
            "recommendation": (
                "No strong pattern match. Start with brute force, "
                "identify bottlenecks, then optimize."
            ),
        }

    return {
        "matches": matches,
        "primary": matches[0],
        "recommendation": f"Start with {matches[0]['pattern']}: {matches[0]['approach']}",
    }
