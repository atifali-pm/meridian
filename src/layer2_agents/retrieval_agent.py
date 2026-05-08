"""Retrieval agent. Phase 1: single-shot pgvector similarity search.

Phase 2 will add tsvector + Reciprocal Rank Fusion. This module is shaped so
the public function (`retrieve`) can grow to a hybrid retriever without
changing callers.
"""
from __future__ import annotations

from typing import Any

import psycopg

from src.config import settings
from src.schemas.state import AgentOutput, Citation, Task


def _embed(text: str) -> list[float]:
    """Phase 1 deterministic pseudo-embedder. Phase 2 swaps in real Voyage embeddings."""
    import hashlib

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [b / 255.0 - 0.5 for b in digest]
    vec = (raw * ((settings.embedding_dim // len(raw)) + 1))[: settings.embedding_dim]
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def search_corpus(query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Return top-k chunks from the seeded corpus by cosine similarity."""
    qvec = _embed(query)
    qlit = _vector_literal(qvec)

    sql = """
        SELECT id, source, content, 1 - (embedding <=> %s::vector) AS score
        FROM corpus_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(sql, (qlit, qlit, top_k))
        rows = cur.fetchall()

    return [
        {"id": r[0], "source": r[1], "content": r[2], "score": float(r[3])}
        for r in rows
    ]


def run_retrieval_task(task: Task) -> AgentOutput:
    """Execute a retrieval task and return its agent output with citations."""
    hits = search_corpus(task.description)

    citations = [
        Citation(
            source_id=h["source"],
            source_kind="corpus",
            snippet=h["content"][:300],
            score=h["score"],
        )
        for h in hits
    ]

    summary = (
        f"Retrieved {len(hits)} chunk(s) from the internal corpus for: {task.description}"
        if hits
        else f"No corpus matches for: {task.description}"
    )

    return AgentOutput(
        task_id=task.id,
        agent_kind="retrieval",
        summary=summary,
        citations=citations,
        raw={"query": task.description, "top_k": len(hits)},
    )
