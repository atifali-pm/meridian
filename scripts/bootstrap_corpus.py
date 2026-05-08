"""Bootstrap a small seeded corpus into pgvector for Phase 1 smoke tests.

Idempotent: drops and recreates the corpus_chunks table on every run. Uses the
deterministic pseudo-embedder so this script needs no external API key.

Usage:
    python -m scripts.bootstrap_corpus
"""
from __future__ import annotations

import psycopg

from src.config import settings
from src.layer2_agents.retrieval_agent import _embed, _vector_literal


SEED_CORPUS: list[tuple[str, str]] = [
    (
        "meridian-spec",
        "Meridian is a production-grade multi-agent research and execution pipeline. "
        "It accepts a high-level business goal, plans a dependency-aware DAG of tasks, "
        "delegates work to specialist sub-agents, and returns a verifiable answer with "
        "provenance and an LLM-as-judge rubric score.",
    ),
    (
        "meridian-stack",
        "The Meridian stack is Python 3.12 with FastAPI and Pydantic v2 on the web "
        "layer. LangGraph drives orchestration. Retrieval uses Postgres 16 plus pgvector "
        "and tsvector with Reciprocal Rank Fusion. Redis 7 holds session state. Langfuse "
        "captures traces, token usage, latency, and retries.",
    ),
    (
        "meridian-models",
        "Claude Opus 4.7 acts as planner and as the LLM-as-judge. Claude Sonnet 4.6 "
        "powers the specialist agents. Claude Haiku 4.5 handles cheap subtasks where "
        "rubric quality tolerates a smaller model. Tavily provides external web search.",
    ),
    (
        "meridian-failure-modes",
        "Meridian handles four adversarial cases: a broken tool that returns 5xx, an "
        "ambiguous goal that requires clarification, a retrieval conflict between two "
        "sources, and incomplete data where the synthesis agent must say so explicitly. "
        "A replanner node fires when any specialist reports failure.",
    ),
    (
        "meridian-provenance",
        "Every fact in the final answer must carry which agent produced it and which "
        "source backs it. Citations include source id, source kind (corpus, web, api), "
        "a snippet, and a score. Synthesis fails the judge if it loses provenance.",
    ),
    (
        "rrf-explained",
        "Reciprocal Rank Fusion combines ranked lists by summing 1 / (k + rank) for "
        "each item across input lists. It is robust to score-scale mismatch between "
        "BM25-like text search and dense vector cosine similarity, which is why it "
        "is the default fusion strategy for hybrid retrieval over pgvector + tsvector.",
    ),
    (
        "langgraph-state",
        "LangGraph state is a typed object passed between nodes. Reducers on list "
        "fields let multiple nodes append outputs without overwriting each other. "
        "Plan-and-Execute with an explicit replanner node is more debuggable than a "
        "ReAct interleaved chain when adversarial inputs hit a tool boundary.",
    ),
]


DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS corpus_chunks;

CREATE TABLE corpus_chunks (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(%(dim)s) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def main() -> None:
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL % {"dim": settings.embedding_dim})
            for source, content in SEED_CORPUS:
                vec = _embed(content)
                cur.execute(
                    "INSERT INTO corpus_chunks (source, content, embedding) VALUES (%s, %s, %s::vector)",
                    (source, content, _vector_literal(vec)),
                )
        conn.commit()
    print(f"Seeded {len(SEED_CORPUS)} chunks into corpus_chunks.")


if __name__ == "__main__":
    main()
