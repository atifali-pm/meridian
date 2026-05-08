"""Typed LangGraph state and DAG schema for Meridian.

State is a single Pydantic v2 model that flows through the graph. Each node
returns a partial dict that LangGraph merges into the running state. Reducers
on list fields ensure agent outputs accumulate rather than overwrite.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TaskKind = Literal["retrieval", "web", "synthesis"]
TaskStatus = Literal["pending", "running", "done", "failed"]


class Task(BaseModel):
    """One node in the planner-produced DAG."""

    id: str = Field(default_factory=lambda: f"t-{uuid4().hex[:8]}")
    kind: TaskKind
    description: str
    acceptance_criteria: str
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = "pending"


class Plan(BaseModel):
    """Planner output. A DAG of tasks plus the final answer shape."""

    goal: str
    tasks: list[Task]
    final_answer_shape: str = Field(
        description="One sentence describing what the final synthesized answer should contain."
    )


class Citation(BaseModel):
    """Provenance unit. Every fact in the final answer must trace to one of these."""

    source_id: str
    source_kind: Literal["corpus", "web", "api"]
    snippet: str
    score: float | None = None


class AgentOutput(BaseModel):
    """A specialist agent's contribution. Citations carry provenance forward."""

    task_id: str
    agent_kind: TaskKind
    summary: str
    citations: list[Citation] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


def _append(left: list, right: list) -> list:
    """LangGraph reducer: concat instead of replace."""
    return (left or []) + (right or [])


class GraphState(BaseModel):
    """The single state object that flows through the orchestration graph."""

    run_id: str = Field(default_factory=lambda: f"run-{uuid4().hex[:8]}")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    goal: str
    plan: Plan | None = None
    agent_outputs: Annotated[list[AgentOutput], _append] = Field(default_factory=list)

    final_answer: str | None = None
    confidence: float | None = None
    error: str | None = None
