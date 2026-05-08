"""LangGraph assembly for Meridian's Phase 1 happy path.

Graph shape:
    plan -> execute_retrieval -> execute_synthesis -> END

Phase 2 will add a router that fans out across multiple specialist tasks and
loops back through a replanner node when any task fails. The state shape is
already designed to support that (list reducers on agent_outputs).
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.layer1_orchestrator.planner import plan_goal
from src.layer2_agents.retrieval_agent import run_retrieval_task
from src.layer2_agents.synthesis_agent import run_synthesis_task
from src.schemas.state import AgentOutput, GraphState, Task


def _node_plan(state: GraphState) -> dict:
    plan = plan_goal(state.goal)
    return {"plan": plan}


def _retrieval_tasks(plan_tasks: list[Task]) -> list[Task]:
    return [t for t in plan_tasks if t.kind == "retrieval"]


def _synthesis_task(plan_tasks: list[Task]) -> Task:
    matches = [t for t in plan_tasks if t.kind == "synthesis"]
    if not matches:
        raise RuntimeError("Planner produced no synthesis task; cannot finalize answer.")
    return matches[-1]


def _node_execute_retrieval(state: GraphState) -> dict:
    if state.plan is None:
        return {"error": "no plan available for retrieval node"}
    outputs: list[AgentOutput] = [run_retrieval_task(t) for t in _retrieval_tasks(state.plan.tasks)]
    return {"agent_outputs": outputs}


def _node_execute_synthesis(state: GraphState) -> dict:
    if state.plan is None:
        return {"error": "no plan available for synthesis node"}

    synth_task = _synthesis_task(state.plan.tasks)
    upstream = [o for o in state.agent_outputs if o.agent_kind != "synthesis"]
    out = run_synthesis_task(synth_task, goal=state.goal, upstream_outputs=upstream)

    return {
        "agent_outputs": [out],
        "final_answer": out.summary,
        "confidence": float(out.raw.get("confidence", 0.0)),
    }


def build_graph():
    """Compile and return the Phase 1 orchestration graph."""
    graph = StateGraph(GraphState)
    graph.add_node("plan", _node_plan)
    graph.add_node("execute_retrieval", _node_execute_retrieval)
    graph.add_node("execute_synthesis", _node_execute_synthesis)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute_retrieval")
    graph.add_edge("execute_retrieval", "execute_synthesis")
    graph.add_edge("execute_synthesis", END)

    return graph.compile()


def run_goal(goal: str) -> GraphState:
    """Run the orchestration graph for a single goal and return the final state."""
    compiled = build_graph()
    initial = GraphState(goal=goal)
    result = compiled.invoke(initial)
    if isinstance(result, GraphState):
        return result
    return GraphState.model_validate(result)
