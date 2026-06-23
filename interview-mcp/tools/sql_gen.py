from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from tools.architecture import _infer_resource_name

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _detect_entities(description: str) -> dict:
    text = description.lower()
    has_users = any(w in text for w in ("user", "member", "patron", "customer"))
    has_copies = any(w in text for w in ("copy", "copies", "inventory", "stock"))
    has_borrow = any(w in text for w in ("borrow", "checkout", "lend", "return"))
    has_reservation = "reserv" in text
    return {
        "has_users": has_users,
        "has_copies": has_copies or has_borrow,
        "has_borrow": has_borrow,
        "has_reservation": has_reservation,
        "resource": _infer_resource_name(description),
    }


def generate_sql_schema(description: str) -> dict:
    """Generate normalized SQL schema, indexes, and sample transactional queries."""
    entities = _detect_entities(description)
    singular = entities["resource"].rstrip("s")

    ctx = {
        "description": description.strip() or "Interview schema",
        "resource": entities["resource"],
        "singular": singular,
        **entities,
    }

    ddl = _env.get_template("sql_schema.sql.j2").render(**ctx)

    sample_queries = []
    if entities["has_borrow"]:
        sample_queries.extend(
            [
                {
                    "name": "borrow_copy",
                    "sql": f"""BEGIN;
SELECT id FROM {singular}_copies
  WHERE {singular}_id = $1 AND status = 'available'
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
-- if found: UPDATE copy status, INSERT borrow_record
COMMIT;""",
                },
                {
                    "name": "return_copy",
                    "sql": f"""UPDATE borrow_records
SET returned_at = NOW(), status = 'returned'
WHERE copy_id = $1 AND status = 'active'
RETURNING id;""",
                },
            ]
        )

    indexes = [
        f"CREATE INDEX idx_{entities['resource']}_created_at ON {entities['resource']}(created_at);",
    ]
    if entities["has_copies"]:
        indexes.append(
            f"CREATE INDEX idx_{singular}_copies_status ON {singular}_copies(status, {singular}_id);"
        )
    if entities["has_borrow"]:
        indexes.append(
            "CREATE INDEX idx_borrow_records_active ON borrow_records(copy_id) WHERE status = 'active';"
        )

    return {
        "description": ctx["description"],
        "ddl": ddl,
        "indexes": indexes,
        "sample_queries": sample_queries,
        "notes": [
            "Use transactions for borrow/return to prevent double-checkout.",
            "Partial index on active borrows speeds availability checks.",
            "Add version column for optimistic locking if needed.",
        ],
    }
