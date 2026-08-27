# syntax=docker/dockerfile:1
FROM base_image

ENV FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000 \
    MCP_TRANSPORT=sse

COPY jira/client/ ./client/
COPY jira/tasks/ ./tasks/
COPY jira/server.py .

EXPOSE 8000
CMD ["python", "server.py"]
