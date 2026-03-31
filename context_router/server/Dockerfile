# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Multi-stage build using openenv-base (REQUIRED by hackathon rules).
# Keep this base image line; provide the image locally by tagging:
#   docker tag ghcr.io/meta-pytorch/openenv-base:latest openenv-base:latest
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app/env

# Build argument to control whether we're building standalone or in-repo
ARG BUILD_MODE=in-repo
ARG ENV_NAME=context_router

# Copy environment code (build context root is the env folder).
COPY . .
    
RUN if [ -f uv.lock ]; then uv sync --frozen; else uv sync; fi

# Avoid copying the virtualenv twice:
# - we copy `/app/.venv` into the runtime image
# - we copy `/app/env` (code) without `.venv`
RUN mv .venv /app/.venv

# Final runtime stage
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy the environment code
COPY --from=builder /app/env /app/env

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set PYTHONPATH so imports work correctly
ENV PYTHONPATH="/app/env:$PYTHONPATH"

# Run as a non-root user in runtime.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Expose server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,socket; socket.create_connection(('127.0.0.1', int(os.getenv('PORT','8000'))), timeout=2).close()" || exit 1

# Run the FastAPI server.
# Use the installed package module path so relative imports inside the package work.
CMD ["uvicorn", "context_router.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
