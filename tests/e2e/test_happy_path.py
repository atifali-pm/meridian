"""Happy-path smoke test for Phase 1.

Runs under any LLM_PROVIDER. Defaults to mock so CI stays green without secrets.
For a live run set LLM_PROVIDER=anthropic (with ANTHROPIC_API_KEY) or
LLM_PROVIDER=groq (with GROQ_API_KEY) before invoking pytest.

Requires the docker compose stack running with seeded corpus
(run scripts/bootstrap_corpus.py first).
"""
from __future__ import annotations

import os

from src.layer1_orchestrator.graph import run_goal


os.environ.setdefault("LLM_PROVIDER", "mock")


def test_happy_path_returns_grounded_answer() -> None:
    state = run_goal("Summarize what Meridian is and what models power its agents.")

    assert state.plan is not None, "Planner produced no plan."
    assert any(t.kind == "retrieval" for t in state.plan.tasks), "Plan missing retrieval task."
    assert any(t.kind == "synthesis" for t in state.plan.tasks), "Plan missing synthesis task."

    assert state.final_answer, "No final answer produced."
    assert state.confidence is not None, "No confidence score produced."
    assert 0.0 <= state.confidence <= 1.0, f"Confidence out of range: {state.confidence}"

    synth_outputs = [o for o in state.agent_outputs if o.agent_kind == "synthesis"]
    assert synth_outputs, "Synthesis agent produced no output."
    assert synth_outputs[-1].citations, "Final answer has no citations; provenance lost."
