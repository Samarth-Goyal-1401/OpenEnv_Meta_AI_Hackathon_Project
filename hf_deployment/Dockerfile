FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml ./
COPY uv.lock* ./

# Use lockfile if present, otherwise resolve deps on the fly
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev --no-install-project; else uv sync --no-dev --no-install-project; fi

COPY . .
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT','8000'))), timeout=2).close()" || exit 1

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
