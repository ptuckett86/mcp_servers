# System Design Checklist

Use with `advise_architecture` MCP tool. Full signals in `interview-mcp/knowledge/arch_signals.yaml`.

## Requirements (5 min)

- [ ] Functional: core user actions
- [ ] Non-functional: scale (QPS), latency, consistency, availability
- [ ] Out of scope: what you will NOT build

## High-level design (10 min)

- [ ] Draw: client → API → services → DB/cache/queue
- [ ] Identify read vs write paths
- [ ] Choose monolith vs services (default: monolith for interviews)

## Data model (10 min)

- [ ] Entities and relationships (1:N, M:N)
- [ ] Normalization vs denormalization tradeoff
- [ ] Indexes for hot queries
- [ ] Call `generate_sql_schema` for DDL starter

## API design (5 min)

- [ ] REST resources and verbs
- [ ] Idempotency for retries (POST borrow with idempotency key)
- [ ] Pagination, filtering on list endpoints
- [ ] Call `generate_fastapi_scaffold` for code starter

## Deep dives (15 min)

Pick 2–3 based on problem:

| Topic | Watch for |
|-------|-----------|
| Consistency | Transactions, row locks, optimistic versioning |
| Caching | Cache-aside, invalidation, hot keys |
| Async | Queue + worker, DLQ, idempotent consumers |
| File upload | Presigned S3 URLs, metadata in DB |
| Auth | JWT vs sessions, RBAC |
| Rate limiting | Token bucket per user/IP |

## Bottlenecks to mention

- N+1 queries
- Double borrow / oversell without locking
- Synchronous side effects in request path
- Missing pagination
- Single DB primary for all reads and writes

## AWS mapping (when asked)

| Need | Service |
|------|---------|
| API | API Gateway / ALB |
| Compute | ECS / Lambda |
| DB | RDS Postgres |
| Cache | ElastiCache Redis |
| Queue | SQS |
| Files | S3 + CloudFront |
| Auth | Cognito |

## Closing

- [ ] Summarize tradeoffs made
- [ ] State what you'd monitor (latency, error rate, queue depth)
- [ ] Mention one future scaling step (read replicas, sharding, cache)
