ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --frozen; else uv sync; fi

COPY . .

EXPOSE 8000
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1
CMD ["uvicorn", "context_router.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

