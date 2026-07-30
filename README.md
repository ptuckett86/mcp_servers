# MCP Servers

GitHub and Jira MCP servers, run together via Docker Compose (SSE). Cursor connects to localhost ports.

## Layout

```
mcp_servers/
├── docker-compose.yml
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

3. Cursor MCP config (global `~/.cursor/mcp.json` and [`.cursor/mcp.json`](.cursor/mcp.json)) should point at those URLs. Reload MCP after compose is up.

```bash
docker compose ps
docker compose logs -f
docker compose down
```

## Tools

### github-assistant (`github`)

| Tool | Description |
|------|-------------|
| `propose_pr_comment_solutions` | Read PR comments and propose solutions |
| `review_pull_request` | Scan PR for security issues, violations, logic gaps |

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
- Rebuild after code changes: `docker compose up -d --build`
