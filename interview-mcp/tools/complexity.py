from __future__ import annotations

import re

from tools.knowledge import load_snippets


def _score_snippet(query: str, snippet: dict) -> tuple[int, list[str]]:
    text = query.lower()
    matched: list[str] = []
    score = 0

    for kw in snippet.get("keywords", []):
        if kw.lower() in text:
            matched.append(kw)
            score += 2

    name_words = snippet.get("name", "").lower().split()
    for word in name_words:
        if len(word) > 3 and word in text:
            matched.append(word)
            score += 1

    if snippet.get("id", "").replace("_", " ") in text:
        score += 3

    return score, matched


def lookup_snippet(query: str) -> dict:
    """Look up interview code snippets by keyword or problem type.

    Returns matching snippets with code, pattern, and complexity talking points.
    """
    if not query.strip():
        return {"matches": [], "hint": "Try: trie, bfs, median, balanced brackets, tree height"}

    scored: list[tuple[int, dict, list[str]]] = []
    for snippet in load_snippets():
        score, matched = _score_snippet(query, snippet)
        if score > 0:
            scored.append((score, snippet, matched))

    scored.sort(key=lambda x: (-x[0], x[1]["name"]))

    matches = []
    for score, snippet, matched in scored[:5]:
        entry = {
            "id": snippet["id"],
            "name": snippet["name"],
            "pattern": snippet.get("pattern", ""),
            "matched_keywords": matched,
            "time_complexity": snippet.get("time_complexity", ""),
            "space_complexity": snippet.get("space_complexity", ""),
            "complexity_explanation": snippet.get("complexity_explanation", ""),
            "code": snippet.get("code", "").strip(),
            "notes": snippet.get("notes", []),
        }
        if snippet.get("optimal_approach"):
            entry["optimal_approach"] = snippet["optimal_approach"].strip()
            entry["optimal_complexity"] = snippet.get("optimal_complexity", "")
        matches.append(entry)

    return {
        "query": query,
        "matches": matches,
        "count": len(matches),
        "interview_tip": (
            "State time and space aloud, then justify with loop structure and data structures used."
            if matches
            else "No match — try pattern name (BFS, trie) or problem keyword (median, brackets)."
        ),
    }


def _heuristic_complexity(code: str) -> list[dict]:
    findings: list[dict] = []
    text = code.lower()

    if "bisect.insort" in code or "insort(" in code:
        findings.append(
            {
                "signal": "bisect.insort on list",
                "time": "O(n) per insert",
                "note": "n inserts → O(n^2) total; mention two-heap O(n log n) alternative",
            }
        )

    if re.search(r"\.pop\(0\)", code):
        findings.append(
            {
                "signal": "list.pop(0)",
                "time": "O(n) per pop",
                "note": "Queue on list is O(n) per dequeue; use collections.deque for O(1)",
            }
        )

    if re.search(r"while\s+.*:\s*\n.*\.replace\(", code, re.MULTILINE):
        findings.append(
            {
                "signal": "while + string replace",
                "time": "O(n * passes)",
                "note": "Repeated scans/replaces; stack approach is O(n)",
            }
        )

    if "def " in code and ("left" in text or "right" in text or "children" in text):
        if code.count("def ") >= 1 and re.search(r"def\s+\w+.*\n.*def\s+\w+|return.*\w+\(", code):
            findings.append(
                {
                    "signal": "recursive tree/graph function",
                    "time": "O(n) nodes visited",
                    "space": "O(h) call stack",
                    "note": "h = height/depth; skewed tree → O(n) space",
                }
            )

    if "visited" in text and ("to_look" in text or "queue" in text or "deque" in text):
        findings.append(
            {
                "signal": "BFS pattern",
                "time": "O(V + E)",
                "space": "O(V)",
                "note": "Each node/edge processed once with visited set",
            }
        )

    if "children" in text and "memo" in text:
        findings.append(
            {
                "signal": "trie / prefix tree",
                "time": "O(L) per operation",
                "space": "O(total chars)",
                "note": "L = key length",
            }
        )

    nested_loops = len(re.findall(r"for\s+\w+\s+in", code))
    if nested_loops >= 2 and "while" not in text:
        findings.append(
            {
                "signal": f"{nested_loops} nested for-loops",
                "time": "O(n^k) typical",
                "note": "Confirm if inner loop runs full n each time",
            }
        )

    if re.search(r"while\s+\w+\s*<", code):
        findings.append(
            {
                "signal": "while loop with counter",
                "time": "O(iterations)",
                "space": "O(1)",
            }
        )

    return findings


def analyze_complexity(code: str, problem: str = "") -> dict:
    """Analyze time/space complexity of code with interview narration points.

    Combines snippet matching, heuristic detection, and talking points
    for explaining complexity aloud in interviews.
    """
    if not code.strip():
        return {"error": "Provide code to analyze."}

    snippet_result = lookup_snippet(problem or code)
    heuristics = _heuristic_complexity(code)

    primary = snippet_result["matches"][0] if snippet_result["matches"] else None

    narration = []
    if primary:
        narration.append(
            f"This looks like {primary['name']} ({primary['pattern']})."
        )
        narration.append(
            f"Time: {primary['time_complexity']}. Space: {primary['space_complexity']}."
        )
        if primary.get("complexity_explanation"):
            narration.append(primary["complexity_explanation"])
        if primary.get("optimal_complexity"):
            narration.append(
                f"If optimized: {primary['optimal_complexity']} — know the tradeoff."
            )
    elif heuristics:
        narration.append("Heuristic analysis from code structure:")
        for h in heuristics:
            parts = [h.get("signal", ""), f"Time: {h['time']}" if h.get("time") else ""]
            if h.get("space"):
                parts.append(f"Space: {h['space']}")
            if h.get("note"):
                parts.append(h["note"])
            narration.append(" — ".join(p for p in parts if p))
    else:
        narration.append(
            "Count primitive operations: loops × work per iteration + recursion depth."
        )

    return {
        "problem": problem or "(inferred from code)",
        "matched_snippet": primary,
        "all_snippet_matches": snippet_result["matches"][:3],
        "heuristic_signals": heuristics,
        "interview_narration": narration,
        "how_to_explain": [
            "1. Identify the input size variable (n, V, E, L, etc.).",
            "2. Count nested loops / recursive branches.",
            "3. Name auxiliary structures (stack, queue, hash map, trie).",
            "4. State time first, then space, then mention optimizations if asked.",
        ],
        "common_followups": [
            "Can you do better?",
            "What is the bottleneck?",
            "What changes for skewed vs balanced tree?",
            "What if input does not fit in memory?",
        ],
    }
