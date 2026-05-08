# Meridian architecture

Status: skeleton. Filled in across Phase 1 through Phase 4.

## System overview

Four layers, mapped one-to-one onto the `src/` tree.

```
                +------------------------+
   business     |  Layer 1: Orchestrator |   plan, dispatch, replan
     goal  -->  |  (LangGraph)           |
                +-----------+------------+
                            |
              +-------------+-------------+
              |             |             |
        +-----v-----+ +-----v-----+ +-----v-----+
        | Retrieval | |  Web/API  | | Synthesis |   Layer 2: specialists
        |  (hybrid) | | (Tavily)  | | (conflict)|
        +-----+-----+ +-----+-----+ +-----+-----+
              |             |             |
              +------+------+------+------+
                     |             |
            +--------v--+   +------v---------+
            | Postgres  |   |     Redis      |   Layer 3: memory
            | + pgvector|   | (session store)|
            +-----------+   +----------------+
                     |             |
              +------v-------------v-------+
              |   Langfuse + LLM judge     |   Layer 4: observability
              |   + run report generator   |
              +----------------------------+
```

## Layer 1: Orchestrator

TODO Phase 1. Capture:

- Why Plan-and-Execute over pure ReAct (debuggability under adversarial inputs).
- Replanner trigger conditions (low confidence, retry exhausted, conflict unresolved).
- State shape and persistence.

## Layer 2: Specialists

TODO Phase 1+2. Capture:

- Common contract (typed Pydantic I/O, retry, timeout, confidence score).
- Retrieval: hybrid pgvector + tsvector with Reciprocal Rank Fusion. Why RRF over naive concat.
- Web/API: Tavily for search; generic HTTP tool with tenacity for arbitrary REST.
- Synthesis: explicit conflict detection step, weighted reconciliation by source confidence, provenance preservation.

## Layer 3: Memory

TODO Phase 3. Capture:

- Session store (Redis) vs long-term (Postgres) split.
- Redundancy avoidance: cosine similarity threshold (0.92) over question embeddings.
- Per-agent context budget and summarization.

## Layer 4: Observability

TODO Phase 4. Capture:

- Langfuse trace structure (run -> agent -> tool call).
- LLM-as-judge rubric (goal completion, accuracy, coverage, confidence, hallucination risk).
- Run report contents.

## Tradeoffs

TODO. One paragraph per major decision:

- Plan-and-Execute over ReAct
- pgvector + tsvector hybrid over single-mode retrieval
- Native Anthropic structured output over instructor
- Self-hosted Langfuse over hosted alternatives
- Postgres for long-term over SQLite or DuckDB

## Failure recovery

TODO. Catalogue every failure mode and how the system handles it:

- Tool timeout -> retry with backoff -> fallback tool -> replan
- Low specialist confidence -> replan with the specialist's failure context
- Retrieval conflict -> synthesis conflict-resolution step -> flagged in run report
- Judge flags hallucination risk -> response carries explicit warning, not silent
