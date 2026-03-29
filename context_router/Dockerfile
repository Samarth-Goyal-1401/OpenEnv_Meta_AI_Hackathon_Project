# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Multi-stage build using openenv-base (REQUIRED by hackathon rules)
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Copy pyproject.toml and uv.lock for dependency resolution
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv sync
RUN if [ -f uv.lock ]; then \
        uv sync --frozen; \
    else \
        uv sync; \
    fi

# Copy the rest of the application
COPY context_router/ ./context_router/
COPY context_router/server/ ./context_router/server/
COPY context_router/graders/ ./context_router/graders/
COPY context_router/tasks/ ./context_router/tasks/
COPY context_router/baseline/ ./context_router/baseline/

# Final runtime stage
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application
COPY --from=builder /app/context_router /app/context_router

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set PYTHONPATH so imports work correctly
ENV PYTHONPATH="/app:$PYTHONPATH"

# Expose the port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI server
CMD ["uvicorn", "context_router.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
