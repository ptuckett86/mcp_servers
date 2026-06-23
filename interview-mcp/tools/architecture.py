from __future__ import annotations

import re

from tools.knowledge import load_arch_signals


def _score_signal(requirements: str, signal: dict) -> tuple[int, list[str]]:
    text = requirements.lower()
    matched: list[str] = []
    score = 0
    for keyword in signal.get("keywords", []):
        if keyword.lower() in text:
            matched.append(keyword)
            score += 1
    return score, matched


def _infer_resource_name(requirements: str) -> str:
    text = requirements.lower()
    candidates = [
        "books",
        "book",
        "users",
        "user",
        "orders",
        "order",
        "products",
        "product",
        "items",
        "item",
        "borrow_records",
        "reservations",
    ]
    for word in candidates:
        if word in text:
            return word.rstrip("s") + "s" if not word.endswith("s") else word
    return "items"


def advise_architecture(requirements: str) -> dict:
    """Advise on system architecture based on requirement signals.

    Returns suggested components, tradeoffs, bottlenecks, and AWS mappings.
    """
    if not requirements.strip():
        return {"matches": [], "recommendation": "Provide requirements to analyze."}

    scored: list[tuple[int, dict, list[str]]] = []
    for signal in load_arch_signals():
        score, matched = _score_signal(requirements, signal)
        if score > 0:
            scored.append((score, signal, matched))

    scored.sort(key=lambda x: (-x[0], x[1]["name"]))

    matches = []
    all_components: list[str] = []
    all_bottlenecks: list[str] = []
    aws_mapping: dict[str, str] = {}

    for score, signal, matched in scored[:4]:
        matches.append(
            {
                "pattern": signal["name"],
                "confidence": score,
                "matched_keywords": matched,
                "components": signal.get("components", []),
                "tradeoffs": signal.get("tradeoffs", []),
                "bottlenecks": signal.get("bottlenecks", []),
                "aws_mapping": signal.get("aws_mapping", {}),
            }
        )
        all_components.extend(signal.get("components", []))
        all_bottlenecks.extend(signal.get("bottlenecks", []))
        aws_mapping.update(signal.get("aws_mapping", {}))

    def dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    is_backend = bool(matches) or bool(
        re.search(r"\b(api|database|sql|server|service|microservice)\b", requirements.lower())
    )

    recommendation = (
        "Monolith API + Postgres is a solid interview default. "
        "Add Redis cache for read-heavy paths, SQS for async side effects."
        if is_backend
        else "Clarify whether this is a coding or system design problem."
    )

    return {
        "matches": matches,
        "suggested_components": dedupe(all_components),
        "key_bottlenecks": dedupe(all_bottlenecks)[:6],
        "aws_mapping": aws_mapping,
        "inferred_resource": _infer_resource_name(requirements),
        "recommendation": recommendation,
    }
