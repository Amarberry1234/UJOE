FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY uj0e ./uj0e
COPY scripts ./scripts
RUN pip install --no-cache-dir uv && \
    uv pip install .[dev] && \
    useradd -m agent && chown -R agent:agent /app
USER agent
ENV PYTHONUNBUFFERED=1
ENV DATA_ROOT=/app/data
EXPOSE 8081
CMD ["uv", "run", "uvicorn", "uj0e.main:app", "--host", "0.0.0.0", "--port", "8081"]
