# MCP Servers

GitHub and Jira MCP servers, run together via Docker Compose (SSE). Cursor connects to localhost ports.

## Layout

```
mcp_servers/
├── docker-compose.yml
├── Dockerfile.base         # shared pip deps (rebuilds when requirements.txt changes)
├── Dockerfile.test         # one-shot test runner
├── requirements.txt
├── requirements-dev.txt    # + pytest
├── scripts/run_tests.sh
├── .env.example
├── github/
│   ├── client/
│   ├── tasks/
│   ├── tests/
│   └── server.py
└── jira/
    ├── client/
    ├── tasks/
    ├── tests/
    └── server.py
```

## Setup

1. Create env file:

```bash
cp .env.example .env
```

| Variable | Used by | Purpose |
|----------|---------|---------|
| `GITHUB_TOKEN` | github | Personal access token |
| `JIRA_BASE_URL` | jira | e.g. `https://your-domain.atlassian.net` |
| `JIRA_EMAIL` | jira | Atlassian account email |
| `JIRA_API_TOKEN` | jira | [API token](https://id.atlassian.com/manage-profile/security/api-tokens) |

2. Start the stack:

```bash
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| github | http://127.0.0.1:8001/sse |
| jira | http://127.0.0.1:8002/sse |

3. Add the MCP servers to Cursor.

   **Project-level** (recommended): this repo already includes [`.cursor/mcp.json`](.cursor/mcp.json). Open the repo in Cursor and the servers should appear after the stack is running.

   **Global** (all projects): add the same config to `~/.cursor/mcp.json` (create the file if it does not exist):

   ```json
   {
     "mcpServers": {
       "github-assistant": {
         "url": "http://127.0.0.1:8001/sse"
       },
       "jira-assistant": {
         "url": "http://127.0.0.1:8002/sse"
       }
     }
   }
   ```

   If you changed the compose ports, update the URLs to match `GITHUB_MCP_PORT` / `JIRA_MCP_PORT` in `.env`.

   Reload MCP in Cursor after `docker compose up` (Command Palette → **MCP: List Servers** → refresh/reconnect).

```bash
docker compose ps
docker compose logs -f
docker compose down
```

## Tools

### github-assistant (`github`)

| Tool | Description |
|------|-------------|
| `propose_pr_comment_solutions` | Implement unresolved reviewer comments (not yours) in the local repo and stage changes for commit. Pass `dry_run=true` to preview only. |
| `review_pull_request` | Scan PR for security issues, violations, logic gaps |
| `review_pull_request_against_ticket` | Review PR risks and compare implementation against a Jira ticket |
| `trailing_month_pr_metrics` | Avg commits/day, comments, and time-open over your PRs in a trailing window |

Example prompts:

```text
Please review PR https://github.com/7pace/7pace.Timetracker/pull/4873 against ticket https://appfire.atlassian.net/browse/TT-8500

Dry run: use propose_pr_comment_solutions on https://github.com/org/repo/pull/123
use propose_pr_comment_solutions on https://github.com/org/repo/pull/123
```

`review_pull_request_against_ticket` needs `GITHUB_TOKEN` plus `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` in `.env`.

Say **Dry run** (or pass `dry_run=true`) to preview the plan without editing or staging files.

### jira-assistant (`jira`)

| Tool | Description |
|------|-------------|
| `review_ticket` | Describe what a Jira ticket is asking for |
| `summarize_ticket_comments` | Summarize ticket discussion |

## Tests

Suites live under `github/tests/` and `jira/tests/`.

```bash
# Docker (recommended)
docker compose --profile test run --rm tests

# Locally (uses .venv if present)
./scripts/run_tests.sh
```

## Extending

- New GitHub tools → `github/tasks/` + register in `github/server.py`
- New Jira tools → `jira/tasks/` + register in `jira/server.py`
- Rebuild after code changes: `docker compose up -d --build github jira` (fast — only app layers rebuild unless `requirements.txt` changed)
- Rebuild Python deps: change `requirements.txt`, then `docker compose build base`
