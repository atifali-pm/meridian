# Scaling design

Status: skeleton. Filled in during Phase 5 as the one-page scaling design doc.

Target shape: one page, four sections, no fluff.

## 1. 10x traffic

TODO. Capture:

- Where the bottleneck moves first (planner LLM tokens, pgvector scan, Tavily quota).
- Horizontal scaling story for the API tier (stateless FastAPI behind a load balancer).
- Connection-pool sizing for Postgres under concurrency.

## 2. Concurrency

TODO. Capture:

- Per-run isolation via Redis namespacing.
- Async fan-out across specialists in Layer 2 (asyncio.gather on independent DAG nodes).
- Backpressure when one specialist saturates (token-bucket per agent).

## 3. Queueing

TODO. Capture:

- When to move from synchronous /run to a job queue (Celery or RQ on Redis).
- Run-status polling endpoint shape.
- Retry semantics across queue restarts (idempotency keys per run).

## 4. Caching

TODO. Capture:

- Embedding cache (question -> embedding, content-addressed).
- Tool-call cache (Tavily query -> result, TTL by query type).
- Plan cache (goal hash -> plan DAG, invalidated on planner version bump).
