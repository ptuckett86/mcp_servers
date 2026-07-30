"""Jira MCP server — ticket review and comment summaries (SSE)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

from tasks.ticket_comments import summarize_ticket_comments  # noqa: E402
from tasks.ticket_review import review_ticket  # noqa: E402

mcp = FastMCP(
    "jira-assistant",
    host=os.environ.get("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
mcp.tool()(review_ticket)
mcp.tool()(summarize_ticket_comments)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    mcp.run(transport=transport)  # type: ignore[arg-type]
