"""GitHub MCP server — PR review changes, security/code review, and metrics (SSE)."""

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

from tasks.pr_comments import propose_pr_comment_solutions  # noqa: E402
from tasks.pr_metrics import trailing_month_pr_metrics  # noqa: E402
from tasks.pr_review import review_pull_request  # noqa: E402
from tasks.pr_ticket_review import review_pull_request_against_ticket  # noqa: E402

mcp = FastMCP(
    "github-assistant",
    host=os.environ.get("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("FASTMCP_PORT", "8000")),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
mcp.tool()(propose_pr_comment_solutions)
mcp.tool()(review_pull_request)
mcp.tool()(review_pull_request_against_ticket)
mcp.tool()(trailing_month_pr_metrics)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")
    mcp.run(transport=transport)  # type: ignore[arg-type]
