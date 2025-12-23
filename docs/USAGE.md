# UJOE Platform Usage

This repository bundles a full local agent stack. The defaults prioritize CPU-first deployments with options for GPU acceleration when available.

## Components
- **Model server (CPU)**: `llama.cpp` exposing an OpenAI-compatible API on `http://model-cpu:8000/v1`. Place a GGUF in `./models` and set `MODEL_FILENAME`.
- **Model server (GPU)**: Optional `vLLM` service (Compose profile `gpu`) using `MODEL_ID` from Hugging Face.
- **Agent API**: FastAPI service on `http://localhost:8081` orchestrating tools and auto-correction loops.
- **Vector store**: Chroma (HTTP + persistent volume `./data/chroma`).
- **Observability**: Prometheus (`http://localhost:9090`), Grafana (`http://localhost:3000`), OTLP collector, and structured logs.
- **UI shell**: `ui/` is wired for static hosting or embedding into a future front-end.

## Running locally
```bash
docker compose up -d
# for GPU vLLM
# docker compose --profile gpu up -d
```

Environment variables (see `.env.example`):
- `MODEL_FILENAME`: GGUF file name inside `./models` for CPU serving.
- `MODEL_ID`: Hugging Face repo id for vLLM (e.g., `TheBloke/Mistral-7B-Instruct-v0.1-AWQ`).
- `MODEL_MAX_TOKENS`: Token cap enforced by the orchestrator.
- `SANDBOX_MEMORY`, `SANDBOX_CPUS`, `SANDBOX_TIMEOUT`: Limits for sandboxed code.
- `DATA_ROOT`: Root for allowed file access.

## Agent API
- `POST /agent/run`: Run a goal-driven loop.
  ```bash
  curl -X POST http://localhost:8081/agent/run \
    -H "Content-Type: application/json" \
    -d '{"goal": "Lister les fichiers autorisés", "max_iters": 2}'
  ```
- `POST /ingest`: Trigger ingestion into Chroma from `data/docs` (or a provided path).
- `GET /health`: Liveness + downstream dependency checks (model, vector store).

## Data pipeline
- Ingest authorized documents:
  ```bash
  uv run python scripts/ingest.py --path data/docs --collection knowledge --chunk-size 800
  ```
- Incremental updates store SHA256 fingerprints in Chroma metadata; reruns skip unchanged files.
- Cleanup an index:
  ```bash
  uv run python scripts/cleanup.py --collection knowledge
  ```

## Auto-correction loop
- The orchestrator generates a plan, executes tools, runs tests/linters, captures stderr/stdout, and retries with a ReAct/tree-of-thought strategy until `max_iters` or success.
- Traces are emitted via OpenTelemetry; metrics count retries, tool invocations, and failures.

## Observability
- Metrics exposed at `/metrics` on the agent service; Prometheus scrapes automatically when Compose is up.
- Grafana is pre-provisioned to scrape Prometheus (admin/admin by default); add dashboards for token usage and sandbox exits.

## Security & guardrails
- Sandboxed code uses `docker run --rm --network none` with CPU/memory/time caps; falls back to `firejail` if available.
- File access is restricted to `DATA_ROOT` (defaults to `./data`); attempts outside are rejected.
- Token quotas enforced via `MODEL_MAX_TOKENS`; watchdog timers abort long tool calls.
- Audit log stored at `./logs/audit.log` summarizing tool invocations and outcomes.

## CI hooks
- `make test` runs unit tests and a minimal end-to-end dry-run.
- `make lint` runs Ruff + Black.
- `make bench` runs a local benchmark scenario using cached prompts and the model API.

## Troubleshooting
- If the model server is unreachable, ensure `MODEL_FILENAME` exists (CPU) or that the GPU profile is enabled.
- If Docker is unavailable for sandboxing, the sandbox tool exits with a clear error and the agent will refuse to execute code.
