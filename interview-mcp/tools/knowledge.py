from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@lru_cache(maxsize=1)
def load_dsa_patterns() -> list[dict]:
    path = KNOWLEDGE_DIR / "dsa_patterns.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("patterns", [])


@lru_cache(maxsize=1)
def load_arch_signals() -> list[dict]:
    path = KNOWLEDGE_DIR / "arch_signals.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("signals", [])


@lru_cache(maxsize=1)
def load_snippets() -> list[dict]:
    path = KNOWLEDGE_DIR / "snippets.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("snippets", [])
