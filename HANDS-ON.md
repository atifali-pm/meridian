# Meridian: hands-on build guide

Read this first. Everything you need to start the next session is in this file.

## Screenshots

When you hit a milestone with visible output (run report rendered, Langfuse trace screenshot, judge rubric JSON pretty-printed in a UI, FastAPI Swagger view of the orchestrator endpoints), capture a screenshot and save it to `/screenshots/` at the repo root. Use descriptive filenames like `01-run-report.png`, `02-langfuse-trace.png`, `03-judge-rubric.png`, `04-orchestrator-graph.png`.

**Embed every screenshot in README.md** via relative markdown image refs: `![Run report](screenshots/01-run-report.png)`. A public repo with screenshots embedded in the README is a complete portfolio artifact. **A live deploy URL is optional, not required.** Most viewers who land on the GitHub page see the system in action through the README; that IS the demo.

`/screenshots/` is the one canonical location for source image files. Do not duplicate them into `/docs/` or `/public/`. The README and the portfolio site both reference them from `/screenshots/` (the portfolio-maintainer copies them to the site's public dir at promotion time).

The portfolio-maintainer at `~/projects/portfolio/.claude/agents/portfolio-maintainer.md` looks in `/screenshots/` when deciding whether to promote the project to atifali.pages.dev. No screenshots = the project does not qualify.

## Preflight

1. Python 3.12 available (`python3.12 --version`).
2. Docker + docker-compose installed.
3. Ports free: 8030 (API), 5455 (Postgres), 6381 (Redis), 3030 (Langfuse). Check with `ss -tlnp | grep -E '8030|5455|6381|3030'`.
4. `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` available. Drop them into `.env` (gitignored).

## Kickoff prompt for the next Claude session

Paste this verbatim into a fresh `claude` session inside `/home/atif/projects/meridian/`:

```
Read HANDS-ON.md, README.md, and the per-project memory at
~/.claude/projects/-home-atif-projects-meridian/memory/project_meridian.md
before doing anything. We are at the end of Phase 1 (orchestrator + retrieval +
synthesis happy path complete, mock smoke test passing). The next milestone is
Phase 2: web/API agent, hybrid retrieval (pgvector + tsvector + RRF), and
adversarial test fixtures with a replanner loop.

Start by:
1. Adding tsvector column + GIN index to corpus_chunks; reseed via
   `scripts/bootstrap_corpus.py`.
2. Implementing Reciprocal Rank Fusion in `src/layer2_agents/retrieval_agent.py`
   (merge pgvector and tsvector ranked lists with k=60).
3. Building `src/layer2_agents/web_agent.py` (Tavily + generic httpx tool with
   tenacity retry and timeout).
4. Adding adversarial fixtures in `tests/e2e/test_adversarial.py` (broken tool,
   ambiguous goal, retrieval conflict, incomplete data).
5. Adding a replanner node to `src/layer1_orchestrator/graph.py` that loops
   when any specialist reports failure.

Memory layer, observability, and judge come in later phases. Do not over-
build Phase 2.
```

## Running Phase 1 locally

```
docker compose -f docker/docker-compose.yml up -d
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.bootstrap_corpus   # seed the pgvector corpus

# Mock mode (no LLM key required, deterministic):
LLM_PROVIDER=mock .venv/bin/python -m pytest tests/e2e/test_happy_path.py -v

# Live mode (set ANTHROPIC_API_KEY or GROQ_API_KEY in .env first):
LLM_PROVIDER=anthropic .venv/bin/python -m pytest tests/e2e/test_happy_path.py -v
LLM_PROVIDER=groq      .venv/bin/python -m pytest tests/e2e/test_happy_path.py -v

# API:
.venv/bin/uvicorn src.api.main:app --reload --port 8030
curl -X POST http://localhost:8030/run \
     -H 'content-type: application/json' \
     -d '{"goal":"Summarize what Meridian is and what models power its agents."}'
```

## Phase plan

### Phase 0: scaffold (current)

- [x] Repo created, public, pushed to `atifali-pm/meridian`
- [x] README, HANDS-ON, .gitignore, LICENSE
- [x] 4-layer `src/` skeleton with empty package dirs
- [x] FastAPI hello-world (`uvicorn src.api.main:app --reload --port 8030`)
- [x] docker-compose stub for postgres + redis + langfuse
- [x] `docs/ARCHITECTURE.md`, `docs/SCALING.md`, `docs/RUN_REPORT_SAMPLE.md` skeletons
- [x] Per-project Claude memory dir populated

### Phase 1: orchestrator + retrieval (single happy path) (DONE 2026-05-08)

- [x] Typed LangGraph state object in `src/schemas/state.py`
- [x] Planner agent (Claude Sonnet) producing task DAG with acceptance criteria
- [x] Single retrieval agent against a small seeded pgvector corpus (`scripts/bootstrap_corpus.py`)
- [x] Synthesis agent with provenance forwarding
- [x] Graph assembly in `src/layer1_orchestrator/graph.py`
- [x] `POST /run` endpoint accepting a goal, returning the final answer
- [x] Smoke test in `tests/e2e/test_happy_path.py` (passes under `LLM_PROVIDER=mock`)
- [x] LLM dispatcher in `src/llm.py` with anthropic + groq + mock backends

### Phase 2: web + synthesis + adversarial

- [ ] Web/API agent (Tavily + generic HTTP tool with retry and timeout)
- [ ] Synthesis agent with explicit conflict detection
- [ ] Hybrid retrieval (pgvector + tsvector + Reciprocal Rank Fusion)
- [ ] Adversarial test fixtures (broken tool, ambiguous goal, retrieval conflict, incomplete data)
- [ ] Replanner loop wired into the graph

### Phase 3: memory & context

- [ ] Redis session store for per-run state
- [ ] Postgres run-log schema
- [ ] Redundancy avoidance via cosine similarity over question embeddings (threshold 0.92)
- [ ] Per-agent context budget + summarization fallback

### Phase 4: observability & evaluation

- [ ] Langfuse instrumentation across all agent calls (token usage, latency, retries)
- [ ] LLM-as-judge (Claude Opus) scoring each run on the rubric
- [ ] Auto-generated run report markdown with trace links, cost estimate, confidence
- [ ] `RUN_REPORT_SAMPLE.md` filled in with a real captured run

### Phase 5: ship

- [ ] Loom walkthrough (8-12 min): architecture, one happy run, one adversarial run, judge output
- [ ] `docs/SCALING.md` filled in (10x traffic, concurrency, queueing, caching)
- [ ] Portfolio site case study (handoff to portfolio-maintainer; only after Phase 4 lands)
- [ ] Upwork Catalog listing under AI Integration once judge + run report are visible

## Known gotchas

- **Anthropic structured output, not instructor.** Use the SDK's native structured output. The JD reviewer will grep for instructor and downgrade for it.
- **Reciprocal Rank Fusion, not naive concat.** When merging pgvector and tsvector results, RRF is the expected fusion. Document the choice in `docs/ARCHITECTURE.md`.
- **Replanner is a separate node, not a ReAct loop.** The JD specifically tests adversarial inputs and broken tools. Plan-and-Execute with an explicit replanner node is more debuggable than ReAct's interleaved chain. Capture this tradeoff in ARCHITECTURE.md.
- **Confidence scores must be in [0, 1] floats, not strings.** The judge rubric expects numeric.
- **Provenance is non-optional.** Every fact in the final answer must carry which agent and which source produced it. The synthesis agent fails the judge if it loses provenance.
- **Don't promote to portfolio site before Phase 2.** An empty case study reads as vapor.
- **Don't promote to Upwork Catalog or Fiverr before Phase 4.** Without judge + run report visible, the listing competes on price alone.
