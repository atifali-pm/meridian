"""Meridian FastAPI entrypoint. Run: uvicorn src.api.main:app --reload --port 8030"""
from fastapi import FastAPI

app = FastAPI(
    title="Meridian",
    description="Production-grade multi-agent research and execution pipeline.",
    version="0.0.1",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "meridian",
        "status": "scaffolded",
        "phase": "0",
        "message": "Phase 0 scaffold. No agents wired yet. See HANDS-ON.md for the build plan.",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
