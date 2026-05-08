"""Synthesis agent. Combines prior agent outputs into the final answer.

Phase 1 scope: a single retrieval feed + a single synthesis call. Phase 2 will
add explicit conflict detection across multiple sources (web vs corpus, source
A vs source B). Provenance is non-optional: the prompt is structured so the
model cannot drop citations without the judge catching it later.

Routes through src.llm.tool_call so swapping providers is a config flip.
"""
from __future__ import annotations

from typing import Any

from src.config import settings
from src.llm import tool_call
from src.schemas.state import AgentOutput, Citation, Task


_SYNTH_SYSTEM = """You are the synthesis agent for Meridian.

Combine the supplied agent outputs into a single concise answer to the user's
goal. Every factual claim in your answer must reference at least one of the
provided source ids inline like [source-id].

Output JSON via the emit_answer tool with these fields:
- answer: the final answer text, with inline [source-id] markers
- confidence: float in [0, 1], your honest estimate
- used_sources: list of source ids you actually cited

If the supplied evidence is insufficient, say so in the answer and lower the
confidence. Never invent sources or claims not backed by the inputs.
"""


_TOOL_SCHEMA: dict[str, Any] = {
    "name": "emit_answer",
    "description": "Return the synthesized answer with citations and confidence.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "used_sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["answer", "confidence", "used_sources"],
    },
}


def _format_evidence(outputs: list[AgentOutput]) -> str:
    blocks: list[str] = []
    for out in outputs:
        blocks.append(f"## Agent: {out.agent_kind} (task {out.task_id})\nSummary: {out.summary}")
        for cite in out.citations:
            blocks.append(f"- [{cite.source_id}] (score={cite.score}): {cite.snippet}")
    return "\n".join(blocks) or "(no evidence gathered)"


def run_synthesis_task(
    task: Task,
    *,
    goal: str,
    upstream_outputs: list[AgentOutput],
) -> AgentOutput:
    """Combine upstream agent outputs into the final answer for the goal."""
    user_prompt = (
        f"Business goal: {goal}\n\n"
        f"Synthesis task: {task.description}\n"
        f"Acceptance criteria: {task.acceptance_criteria}\n\n"
        f"Evidence from upstream agents:\n{_format_evidence(upstream_outputs)}"
    )

    payload = tool_call(
        system=_SYNTH_SYSTEM,
        tool=_TOOL_SCHEMA,
        messages=[{"role": "user", "content": user_prompt}],
        model=settings.anthropic_agent_model,
    )

    used = set(payload.get("used_sources", []))
    forwarded_citations = [
        Citation(source_id=c.source_id, source_kind=c.source_kind, snippet=c.snippet, score=c.score)
        for out in upstream_outputs
        for c in out.citations
        if c.source_id in used
    ]

    return AgentOutput(
        task_id=task.id,
        agent_kind="synthesis",
        summary=payload["answer"],
        citations=forwarded_citations,
        raw={"confidence": float(payload["confidence"]), "used_sources": list(used)},
    )
