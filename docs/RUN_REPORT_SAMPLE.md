# Run report (sample)

Status: placeholder. Filled in during Phase 4 with a real captured run.

The auto-generated report for every run will include the sections below. This file becomes the canonical example once Phase 4 lands.

## Run metadata

- Run ID: `<uuid>`
- Goal: `<original business goal>`
- Started: `<ISO timestamp>`
- Duration: `<seconds>`
- Langfuse trace: `<url>`

## Plan

DAG produced by the planner, with task IDs, dependencies, and acceptance criteria.

## Execution trace

Per-agent, per-tool-call summary including:

- Agent name
- Tool calls (input, output, latency, retries)
- Confidence score
- Fallback events (if any)

## Conflict resolution

If the synthesis agent detected conflicts between sources, the resolution and the weights applied land here.

## Final answer

The structured answer with provenance for every claim.

## Judge rubric

Claude Opus scores on:

- Goal completion (0 to 1)
- Accuracy (0 to 1)
- Coverage (0 to 1)
- Confidence calibration (0 to 1)
- Hallucination risk (0 to 1, lower is better)

Plus a free-text justification per dimension.

## Cost

- Tokens by model (input, output)
- Estimated USD per the per-model pricing table in `src/layer4_observability/pricing.py`
