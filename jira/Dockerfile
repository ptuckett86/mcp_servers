FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000 \
    MCP_TRANSPORT=sse

WORKDIR /app

# Build context is the mcp_servers root (shared requirements.txt).
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY jira/client/ ./client/
COPY jira/tasks/ ./tasks/
COPY jira/server.py .

EXPOSE 8000
CMD ["python", "server.py"]
