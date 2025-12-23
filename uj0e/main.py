from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, generate_latest
from starlette.responses import Response

from .config import settings
from .orchestrator import AgentOrchestrator
from .vector import VectorStore, iter_paths

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UJOE Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
FastAPIInstrumentor.instrument_app(app)

orchestrator = AgentOrchestrator()
registry = CollectorRegistry()
REQUEST_COUNTER = Counter("agent_requests", "Total agent runs", registry=registry)
FAILURES = Counter("agent_failures", "Agent failures", registry=registry)
ITER_GAUGE = Gauge("agent_iterations", "Iterations used", registry=registry)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.model_endpoint, "vector": settings.chroma_url}


@app.post("/agent/run")
def run_agent(goal: str = Body(..., embed=True), max_iters: int = Body(3, embed=True)) -> dict:
    try:
        REQUEST_COUNTER.inc()
        state = orchestrator.run(goal=goal, max_iters=max_iters)
        ITER_GAUGE.set(state.iterations)
        if not state.completed:
            FAILURES.inc()
        return {
            "goal": state.goal,
            "history": state.history,
            "iterations": state.iterations,
            "completed": state.completed,
            "last_result": state.last_result.output if state.last_result else None,
        }
    except Exception as exc:  # noqa: BLE001
        FAILURES.inc()
        logger.exception("agent run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ingest")
def ingest(path: Optional[str] = Body(None, embed=True), collection: str = Body("knowledge", embed=True)) -> dict:
    target = Path(path or settings.data_root)
    store = VectorStore(collection=collection)
    added = store.ingest_files(iter_paths(target))
    return {"added_chunks": added}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
