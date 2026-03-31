ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK CMD python -c "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT','8000'))), timeout=2).close()" || exit 1
CMD ["uvicorn", "context_router.server.app:app", "--host", "0.0.0.0", "--port", "8000"]

