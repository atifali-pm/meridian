"""LLM provider dispatcher.

Single seam for every LLM tool call in Meridian. Selecting the backend is a
config flip (LLM_PROVIDER) and adding a new backend means adding one
implementation here. Anthropic remains the production default; mock is for
offline tests; groq is a free-tier dev option.

The contract is one function: tool_call(system, tool, messages) -> dict.
Every caller wants the parsed tool input, so the dispatcher hides the
response-shape differences between providers.
"""
from __future__ import annotations

import json
import os
from typing import Any

from src.config import settings


def _provider() -> str:
    return os.environ.get("LLM_PROVIDER", "anthropic").lower()


def tool_call(
    *,
    system: str,
    tool: dict[str, Any],
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Run a single forced-tool LLM call and return the parsed tool input.

    `tool` is the Anthropic-shaped schema (name, description, input_schema).
    Each backend translates as needed. Returns the dict that the model placed
    in the tool_use block.
    """
    backend = _provider()
    if backend == "mock":
        return _mock_call(tool=tool, messages=messages)
    if backend == "anthropic":
        return _anthropic_call(system=system, tool=tool, messages=messages, model=model, max_tokens=max_tokens)
    if backend == "groq":
        return _groq_call(system=system, tool=tool, messages=messages, model=model, max_tokens=max_tokens)
    raise ValueError(f"Unknown LLM_PROVIDER: {backend!r}. Expected anthropic|groq|mock.")


def _anthropic_call(
    *,
    system: str,
    tool: dict[str, Any],
    messages: list[dict[str, Any]],
    model: str | None,
    max_tokens: int,
) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=model or settings.anthropic_agent_model,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=messages,
    )

    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None:
        raise RuntimeError(f"Anthropic returned no tool_use block. Raw: {response.model_dump_json()}")
    return block.input if isinstance(block.input, dict) else json.loads(block.input)


def _groq_call(
    *,
    system: str,
    tool: dict[str, Any],
    messages: list[dict[str, Any]],
    model: str | None,
    max_tokens: int,
) -> dict[str, Any]:
    """Call Groq's OpenAI-compatible endpoint with forced tool use.

    Groq exposes Llama 3.3 70B with structured tool use. Free tier is rate-
    limited but generous enough for development smoke tests.
    """
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set; cannot run with LLM_PROVIDER=groq.")

    client = Groq(api_key=api_key)
    openai_tool = {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool["input_schema"],
        },
    }
    openai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        content = m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])
        openai_messages.append({"role": m["role"], "content": content})

    response = client.chat.completions.create(
        model=model or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        max_tokens=max_tokens,
        messages=openai_messages,
        tools=[openai_tool],
        tool_choice={"type": "function", "function": {"name": tool["name"]}},
    )

    choice = response.choices[0]
    if not choice.message.tool_calls:
        raise RuntimeError(f"Groq returned no tool_calls. Raw: {response.model_dump_json()}")
    args = choice.message.tool_calls[0].function.arguments
    return json.loads(args) if isinstance(args, str) else args


def _mock_call(*, tool: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic stub for offline tests. Branches on tool name."""
    name = tool["name"]
    user_text = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user" and isinstance(m["content"], str)),
        "",
    )

    if name == "emit_plan":
        goal = user_text.replace("Goal: ", "", 1).strip() or "unspecified"
        return {
            "goal": goal,
            "tasks": [
                {
                    "id": "t-retrieval",
                    "kind": "retrieval",
                    "description": goal,
                    "acceptance_criteria": "At least one corpus chunk relevant to the goal is returned.",
                    "depends_on": [],
                },
                {
                    "id": "t-synthesis",
                    "kind": "synthesis",
                    "description": "Combine retrieved evidence into a final answer with citations.",
                    "acceptance_criteria": "Answer cites at least one source and includes a confidence score.",
                    "depends_on": ["t-retrieval"],
                },
            ],
            "final_answer_shape": "A short paragraph that addresses the goal with inline [source-id] citations.",
        }

    if name == "emit_answer":
        sources = _extract_sources(user_text)
        cited = sources[:3] if sources else []
        if cited:
            answer = (
                "Mock synthesis answer assembled from corpus evidence. "
                + " ".join(f"Reference [{s}]." for s in cited)
            )
            confidence = 0.6
        else:
            answer = "Mock synthesis: no upstream evidence was supplied; cannot answer."
            confidence = 0.1
        return {"answer": answer, "confidence": confidence, "used_sources": cited}

    raise ValueError(f"Mock backend has no canned response for tool {name!r}.")


def _extract_sources(prompt_text: str) -> list[str]:
    """Pull out [source-id] tokens from the synthesis prompt's evidence block."""
    sources: list[str] = []
    for line in prompt_text.splitlines():
        line = line.strip()
        if line.startswith("- [") and "]" in line:
            sid = line[3 : line.index("]")]
            if sid and sid not in sources:
                sources.append(sid)
    return sources
