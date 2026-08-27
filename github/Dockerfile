# syntax=docker/dockerfile:1
FROM base_image

ENV FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000 \
    MCP_TRANSPORT=sse

COPY github/client/ ./client/
COPY github/tasks/ ./tasks/
COPY jira/client/jira.py ./jira_client.py
COPY github/server.py .

EXPOSE 8000
CMD ["python", "server.py"]
