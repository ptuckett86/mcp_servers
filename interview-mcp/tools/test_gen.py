from __future__ import annotations

from tools.pattern import detect_pattern

TEST_TEMPLATES = {
    "default": {
        "empty": ["[]", '""', "null input if applicable"],
        "single_element": ["[1]", '"a"', "one node/tree"],
        "boundary": ["min/max values", "first/last index", "full capacity"],
        "duplicates": ["all same elements", "repeated values"],
        "negatives": ["negative numbers", "mixed signs"],
        "large_input": ["n=10^5 elements", "stress memory/time limits"],
        "invalid": ["wrong types", "out of range", "malformed input"],
    },
    "sliding window": {
        "empty": ['s=""', "empty array"],
        "single_element": ['s="a"', "[1]"],
        "boundary": ["window size equals array length", "k=0 or k=1"],
        "duplicates": ["all same char", "repeating subsequence"],
        "negatives": ["not applicable unless numbers"],
        "large_input": ["long string n=10^5", "all distinct chars"],
        "invalid": ["k > n", "negative k"],
    },
    "tree": {
        "empty": ["null root"],
        "single_element": ["single node"],
        "boundary": ["skewed left/right", "perfectly balanced"],
        "duplicates": ["duplicate values in BST"],
        "negatives": ["negative node values"],
        "large_input": ["depth 10^4", "complete tree"],
        "invalid": ["cycle in graph disguised as tree"],
    },
    "graph": {
        "empty": ["no nodes", "no edges"],
        "single_element": ["one node isolated"],
        "boundary": ["disconnected components", "self-loop"],
        "duplicates": ["parallel edges", "duplicate neighbors"],
        "negatives": ["negative edge weights"],
        "large_input": ["sparse vs dense graph"],
        "invalid": ["node id out of range"],
    },
    "matrix": {
        "empty": ["0x0 matrix if allowed", "1x1"],
        "single_element": ["1x1 matrix"],
        "boundary": ["single row", "single column", "all zeros"],
        "duplicates": ["identical rows/cols"],
        "negatives": ["negative values"],
        "large_input": ["1000x1000", "sparse matrix"],
        "invalid": ["ragged rows", "non-rectangular"],
    },
}


def _template_key(pattern_name: str) -> str:
    name = pattern_name.lower()
    if "sliding window" in name or "two pointer" in name:
        return "sliding window"
    if "bfs" in name or "dfs" in name or "tree" in name:
        return "tree"
    if "graph" in name or "topological" in name or "union-find" in name:
        return "graph"
    if "matrix" in name:
        return "matrix"
    return "default"


def generate_tests(problem: str, function_signature: str = "") -> dict:
    """Generate categorized test cases for a problem.

    Returns edge, boundary, stress, and invalid input suggestions
    based on detected problem patterns.
    """
    pattern_result = detect_pattern(problem)
    primary = pattern_result.get("primary")
    key = _template_key(primary["pattern"]) if primary else "default"
    template = TEST_TEMPLATES[key]

    categories = {}
    for category, cases in template.items():
        categories[category] = {
            "description": category.replace("_", " ").title(),
            "cases": cases,
        }

    return {
        "function_signature": function_signature or "(infer from problem)",
        "detected_pattern": primary["pattern"] if primary else "Unknown",
        "test_categories": categories,
        "tips": [
            "Write tests before optimizing.",
            "Include at least one failing case you expect before implementing.",
            "For interviews, narrate why each edge case matters.",
        ],
    }
