"""Meridian FastAPI entrypoint. Run: uvicorn src.api.main:app --reload --port 8030"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.layer1_orchestrator.graph import run_goal
from src.schemas.state import GraphState

app = FastAPI(
    title="Meridian",
    description="Production-grade multi-agent research and execution pipeline.",
    version="0.1.0",
)


class RunRequest(BaseModel):
    goal: str = Field(min_length=3, description="High-level business goal to research and answer.")


class RunResponse(BaseModel):
    run_id: str
    goal: str
    final_answer: str | None
    confidence: float | None
    plan: dict | None
    agent_outputs: list[dict]
    error: str | None


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "meridian",
        "status": "phase-1",
        "phase": "1",
        "message": "Phase 1: orchestrator + single retrieval agent wired. POST /run to invoke.",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    try:
        state: GraphState = run_goal(req.goal)
    except Exception as exc:  # surface upstream failure with status code
        raise HTTPException(status_code=500, detail=f"orchestration failed: {exc}") from exc

    return RunResponse(
        run_id=state.run_id,
        goal=state.goal,
        final_answer=state.final_answer,
        confidence=state.confidence,
        plan=state.plan.model_dump() if state.plan else None,
        agent_outputs=[o.model_dump() for o in state.agent_outputs],
        error=state.error,
    )
