# Interview Assistant

MCP server and Cursor Skill for technical interview prep — DSA pattern detection, backend scaffolds, architecture advice, test generation, and solution review.

## What's included

| Component | Purpose |
|-----------|---------|
| **MCP server** (`interview-mcp/`) | 7 deterministic tools (no API keys, works offline) |
| **Cursor Skill** (`.cursor/skills/interview-assistant/`) | Workflow orchestration and interview guardrails |
| **MCP config** | Global: `~/.cursor/mcp.json` (all projects). Project copy: [`.cursor/mcp.json`](.cursor/mcp.json) |

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install dependencies

**Option A — uv (recommended if installed):**

```bash
cd /home/landon-tuckett/Repos/mcp_servers
uv sync
```

**Option B — pip + venv:**

```bash
cd /home/landon-tuckett/Repos/mcp_servers
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The project `.cursor/mcp.json` points at `.venv/bin/python`. Recreate the venv or update the path if your setup differs.

### Enable in Cursor (all projects)

The server is registered **globally** in `~/.cursor/mcp.json`, so it is available in every Cursor project.

1. Install dependencies once (see above).
2. Reload Cursor or open **Settings → MCP** — `interview-assistant` should appear with a green status.
3. If it shows an error, confirm `.venv` exists at `/home/landon-tuckett/Repos/mcp_servers/.venv`.

The **interview-assistant** skill is symlinked to `~/.cursor/skills/interview-assistant` so the workflow also applies in any project. Edits to the skill in this repo take effect everywhere via the symlink.

To use only in this repo (no global install), rely on [`.cursor/mcp.json`](.cursor/mcp.json) instead and remove the entry from `~/.cursor/mcp.json`.

### Verify with MCP Inspector

```bash
uv run mcp dev interview-mcp/server.py
```

Opens a browser UI to call each tool interactively.

## MCP Tools

| Tool | Description |
|------|-------------|
| `interview_analyze` | One-shot: pattern + tests + architecture (if backend) |
| `detect_pattern` | Score problem against DSA pattern knowledge base |
| `generate_tests` | Edge, boundary, stress, and invalid test categories |
| `review_solution` | Senior review checklist + heuristic flags |
| `generate_fastapi_scaffold` | Router, Pydantic schemas, service layer stubs |
| `generate_sql_schema` | Normalized DDL, indexes, transactional queries |
| `advise_architecture` | Components, tradeoffs, bottlenecks, AWS mapping |
| `analyze_complexity` | Time/space Big-O with interview narration |
| `lookup_snippet` | Your past solutions by keyword (BFS, trie, median, etc.) |

## Usage in Cursor

Paste a problem and ask:

- **DSA:** "Analyze this problem: find longest substring without repeating characters"
- **Backend:** "Design a library borrowing API with multiple copies per book"
- **Review:** "Review my solution" (with code attached)
- **Complexity:** "What's the time and space complexity of this code?"
- **Snippet:** "Look up my trie contacts solution"

The **interview-assistant** skill auto-applies on interview-related prompts when working in this repo.

### Recommended workflow

1. `interview_analyze` — before writing code
2. Plan with pseudocode / data model
3. `generate_sql_schema` + `generate_fastapi_scaffold` (backend)
4. Implement business logic
5. `generate_tests` + `review_solution`

## Extending

### Add a DSA pattern

Edit [`interview-mcp/knowledge/dsa_patterns.yaml`](interview-mcp/knowledge/dsa_patterns.yaml):

```yaml
  - name: My Pattern
    signals: [keyword1, keyword2]
    approach: How to solve
    complexity: "Time O(n), Space O(1)"
    pitfalls: [common mistake]
    example_problems: [Example problem name]
```

No Python changes required.

### Add architecture signals

Edit [`interview-mcp/knowledge/arch_signals.yaml`](interview-mcp/knowledge/arch_signals.yaml).

### Add a code snippet

Edit [`interview-mcp/knowledge/snippets.yaml`](interview-mcp/knowledge/snippets.yaml) with `keywords`, `code`, `time_complexity`, `space_complexity`, and `complexity_explanation`.

### Customize scaffolds

Edit Jinja2 templates in [`interview-mcp/templates/`](interview-mcp/templates/).

## Project structure

```
mcp_servers/
├── .cursor/
│   ├── mcp.json
│   └── skills/interview-assistant/
├── interview-mcp/
│   ├── server.py
│   ├── knowledge/
│   ├── templates/
│   └── tools/
├── pyproject.toml
└── README.md
```

## Philosophy

Tools accelerate thinking, not replace it. You should be able to explain every line of generated or reviewed code. Use MCP for pattern recognition, scaffolds, and checklists — then reason and implement yourself.
