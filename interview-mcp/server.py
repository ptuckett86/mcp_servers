"""Interview Assistant MCP Server."""

from mcp.server.fastmcp import FastMCP

from tools.architecture import advise_architecture
from tools.complexity import analyze_complexity, lookup_snippet
from tools.composite import interview_analyze
from tools.fastapi_gen import generate_fastapi_scaffold
from tools.pattern import detect_pattern
from tools.reviewer import review_solution
from tools.sql_gen import generate_sql_schema
from tools.test_gen import generate_tests

mcp = FastMCP("interview-assistant")

mcp.tool()(detect_pattern)
mcp.tool()(review_solution)
mcp.tool()(generate_tests)
mcp.tool()(generate_fastapi_scaffold)
mcp.tool()(generate_sql_schema)
mcp.tool()(advise_architecture)
mcp.tool()(interview_analyze)
mcp.tool()(analyze_complexity)
mcp.tool()(lookup_snippet)

if __name__ == "__main__":
    mcp.run()
