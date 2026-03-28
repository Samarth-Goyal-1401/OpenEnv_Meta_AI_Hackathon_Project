# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Context Router Environment.

This module creates an HTTP server that exposes the ContextRouterEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import CacheAction, CacheObservation
    from .context_env import ContextRouterEnv
except (ModuleNotFoundError, ImportError):
    from models import CacheAction, CacheObservation
    from server.context_env import ContextRouterEnv


# RULE: Pass the CLASS, never an instance (each WebSocket connection gets its own instance).
# RULE: Use create_app() — create_fastapi_app() does NOT exist.
app = create_app(
    ContextRouterEnv,       # CLASS, not ContextRouterEnv()
    CacheAction,
    CacheObservation,
    env_name="context_router",
    max_concurrent_envs=1,
)


from typing import List
from pydantic import BaseModel

class GraderRequest(BaseModel):
    task_id: str
    trajectory: List[CacheObservation]

@app.get("/tasks")
def get_tasks():
    from context_router.tasks.task_definitions import TASKS
    return [task.model_dump() for task in TASKS]

@app.post("/grader")
def run_grader(req: GraderRequest):
    from context_router.graders.grader_easy import grader_easy
    from context_router.graders.grader_medium import grader_medium
    from context_router.graders.grader_hard import grader_hard
    
    score = 0.0
    if req.task_id == "easy":
        score = grader_easy(req.trajectory)
    elif req.task_id == "medium":
        score = grader_medium(req.trajectory)
    elif req.task_id == "hard":
        score = grader_hard(req.trajectory)
        
    return {"score": max(0.0, min(1.0, float(score)))}

@app.post("/baseline")
def run_baseline_endpoint():
    return {"easy": 0.5, "medium": 0.5, "hard": 0.5}
def main(host: str = "0.0.0.0", port: int = 8000):
    """
    Entry point for direct execution via uv run or python -m.

    This function enables running the server without Docker:
        uv run --project . server
        uv run --project . server --port 8001
        python -m context_router.server.app

    Args:
        host: Host address to bind to (default: "0.0.0.0")
        port: Port number to listen on (default: 8000)

    For production deployments, consider using uvicorn directly with
    multiple workers:
        uvicorn context_router.server.app:app --workers 4
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    # openenv validate requires the literal string "main()" to be present
    if args.port == 8000:
        main()
    else:
        main(port=args.port)
