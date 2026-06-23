from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _to_class_name(resource: str) -> str:
    singular = resource.rstrip("s") if resource.endswith("s") and len(resource) > 1 else resource
    return "".join(word.capitalize() for word in re.split(r"[_\s-]+", singular))


def _normalize_resource(resource_name: str, description: str) -> str:
    if resource_name.strip():
        name = resource_name.strip().lower().replace(" ", "_")
        return name if name.endswith("s") else f"{name}s"

    text = description.lower()
    for word in ("books", "users", "orders", "products", "items"):
        if word in text:
            return word
    return "items"


def generate_fastapi_scaffold(description: str, resource_name: str = "") -> dict:
    """Generate FastAPI router, schemas, and service layer scaffolds.

    Returns Python code strings for router.py, schemas.py, and service.py.
    """
    resource = _normalize_resource(resource_name, description)
    class_name = _to_class_name(resource)
    singular = resource.rstrip("s")

    ctx = {
        "resource": resource,
        "singular": singular,
        "class_name": class_name,
        "description": description.strip() or f"CRUD API for {resource}",
    }

    return {
        "resource": resource,
        "description": ctx["description"],
        "files": {
            "router.py": _env.get_template("fastapi_router.py.j2").render(**ctx),
            "schemas.py": _env.get_template("fastapi_schemas.py.j2").render(**ctx),
            "service.py": _env.get_template("fastapi_service.py.j2").render(**ctx),
        },
        "next_steps": [
            f"Wire router into main.py: app.include_router({resource}_router)",
            "Implement DB session dependency and repository calls in service.py",
            "Add auth middleware if requirements mention users/permissions",
        ],
    }
