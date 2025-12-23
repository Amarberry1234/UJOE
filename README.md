# UJOE

Uncle Joe now ships a local-first AI agent stack with sandboxed tooling, local model serving, and observability. Everything runs on your own hardware—no paid cloud dependencies.

## What's inside
- **Model serving**: CPU-first `llama.cpp` with GGUF and an optional GPU `vLLM` profile. Both expose OpenAI-compatible HTTP APIs for the orchestrator.
- **Agent orchestrator**: LangGraph-powered loops with guarded tools (sandboxed code execution, controlled file access, Chroma-backed retrieval) and a ReAct/tree-of-thought style controller.
- **Data pipeline**: Chunking, embedding, FAISS/Chroma indexing, incremental updates, and cleanup scripts.
- **Auto-correction**: Plan → generate → run tests/linters → capture traces/errors → regenerate until success or max iterations.
- **Observability & safety**: Structured logs, OTLP traces, Prometheus metrics/Grafana dashboards, token and time quotas, audit logging.
- **Packaging**: Docker Compose to stand up the model server, agent API, vector store, observability stack, and a minimal UI shell.

## Quick start
1. Place a GGUF model in `models/` (for CPU) or set `MODEL_ID` for `vLLM` (GPU profile).
2. Start the stack:
   ```bash
   docker compose up -d
   # or for GPU vLLM
   docker compose --profile gpu up -d
   ```
3. Ingest documents you are allowed to use:
   ```bash
   uv run python scripts/ingest.py --path data/docs --collection knowledge --chunk-size 800
   ```
4. Hit the agent API:
   ```bash
   curl -X POST http://localhost:8081/agent/run \
     -H "Content-Type: application/json" \
     -d '{"goal": "Résume les notes locales", "max_iters": 3}'
   ```

See [`docs/USAGE.md`](docs/USAGE.md) for full workflows, safety controls, and troubleshooting.
