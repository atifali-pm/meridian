"""Planner agent. Decomposes a business goal into a dependency-aware DAG.

Phase 1 scope: emits a single retrieval task plus a synthesis task. The DAG
machinery is in place so Phase 2 can grow it (web, multi-step retrieval,
conflict resolution) without reshaping the state.

Routes through src.llm.tool_call so swapping providers (anthropic, groq, mock)
is a config flip, not a code change.
"""
from __future__ import annotations

from typing import Any

from src.config import settings
from src.llm import tool_call
from src.schemas.state import Plan, Task


_PLANNER_SYSTEM = """You are the planner for Meridian, a multi-agent research pipeline.

Given a business goal, produce a small dependency-aware DAG of tasks. Each task
has a kind (one of: retrieval, web, synthesis), a description, acceptance
criteria, and a list of task ids it depends on.

Rules:
- A retrieval task pulls facts from the internal corpus.
- A web task uses external search (do NOT emit web tasks in Phase 1).
- A synthesis task combines prior outputs into the final answer. Exactly one
  synthesis task at the end, depending on every non-synthesis task.
- For Phase 1 you may only emit ONE retrieval task plus ONE synthesis task.
- Keep descriptions concrete and verifiable.
"""

_TOOL_SCHEMA: dict[str, Any] = {
    "name": "emit_plan",
    "description": "Return the dependency-aware task DAG for the given goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "kind": {"type": "string", "enum": ["retrieval", "web", "synthesis"]},
                        "description": {"type": "string"},
                        "acceptance_criteria": {"type": "string"},
                        "depends_on": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "kind", "description", "acceptance_criteria", "depends_on"],
                },
            },
            "final_answer_shape": {"type": "string"},
        },
        "required": ["goal", "tasks", "final_answer_shape"],
    },
}


def plan_goal(goal: str) -> Plan:
    """Call the planner LLM and return a validated Plan."""
    payload = tool_call(
        system=_PLANNER_SYSTEM,
        tool=_TOOL_SCHEMA,
        messages=[{"role": "user", "content": f"Goal: {goal}"}],
        model=settings.anthropic_planner_model,
    )

    tasks = [Task(**t) for t in payload["tasks"]]
    return Plan(
        goal=payload["goal"],
        tasks=tasks,
        final_answer_shape=payload["final_answer_shape"],
    )
