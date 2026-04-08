import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openenv.core.env_server import create_app
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from ..graders.grader_easy import grader_easy
    from ..graders.grader_hard import grader_hard
    from ..graders.grader_medium import grader_medium
    from ..models import CacheAction, CacheObservation, EvictionTactic
    from .context_env import ContextRouterEnv
    from ..tasks.task_definitions import TASKS
except (ImportError, ValueError):
    from graders.grader_easy import grader_easy
    from graders.grader_hard import grader_hard
    from graders.grader_medium import grader_medium
    from models import CacheAction, CacheObservation, EvictionTactic
    from server.context_env import ContextRouterEnv
    from tasks.task_definitions import TASKS

logger = logging.getLogger(__name__)
SUPPORTED_TASKS = frozenset({"easy", "medium", "hard"})
MAX_GRADER_TRAJECTORY_LEN = 512
BASELINE_MAX_STEPS = {"easy": ContextRouterEnv.MAX_STEPS, "medium": ContextRouterEnv.MAX_STEPS, "hard": 7}


# RULEBOOK PB1: pass the environment class, never an instance.
app = create_app(ContextRouterEnv, CacheAction, CacheObservation, env_name="context_router")

# ── Dashboard: Mount static files ────────────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Global exception handler (Task 4: prevent 500s) ─────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad request",
            "message": str(exc),
            "done": True,
            "reward": 0.0,
        },
    )


class GraderRequest(BaseModel):
    task_id: str = Field(..., description="Task id: easy | medium | hard")
    trajectory: list[Any] = Field(
        default_factory=list,
        max_length=MAX_GRADER_TRAJECTORY_LEN,
        description=f"Episode observations (max {MAX_GRADER_TRAJECTORY_LEN} steps)",
    )


@app.get("/tasks")
def get_tasks() -> dict[str, list[dict[str, Any]]]:
    return {"tasks": list(TASKS.values())}


# ── Dashboard endpoints ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(str(index_file), media_type="text/html")
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/dashboard/state")
def dashboard_state() -> dict[str, Any]:
    """Return current environment state for the live dashboard."""
    try:
        # Access the environment instance from the app state
        env: ContextRouterEnv | None = getattr(app.state, "env", None)
        if env is None:
            return {
                "vram_utilization": 0.0,
                "incoming_tokens": 0,
                "memory_blocks": [],
                "oom_triggered": False,
                "message": "Environment not initialized. Call /reset first.",
                "step_count": 0,
                "episode_id": "",
                "task_name": "",
            }

        total = sum(b.token_count for b in env._blocks.values())
        return {
            "vram_utilization": max(0.0, min(1.0, total / max(1, env._max_capacity))),
            "incoming_tokens": env._incoming_tokens,
            "memory_blocks": [
                {
                    "block_id": b.block_id,
                    "block_type": b.block_type,
                    "attention_score": b.attention_score,
                    "token_count": b.token_count,
                    "age": b.age,
                }
                for b in env._blocks.values()
            ],
            "oom_triggered": False,
            "message": getattr(env, "_last_message", ""),
            "step_count": env._state.step_count,
            "episode_id": env._state.episode_id,
            "task_name": env._current_task,
        }
    except Exception as e:
        logger.error("dashboard_state error: %s", e, exc_info=True)
        return {
            "vram_utilization": 0.0,
            "incoming_tokens": 0,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": f"Error: {e}",
            "step_count": 0,
            "episode_id": "",
            "task_name": "",
        }


def _to_observation(item: Any) -> CacheObservation:
    if isinstance(item, CacheObservation):
        return item
    if isinstance(item, dict):
        return CacheObservation(
            vram_utilization=float(item.get("vram_utilization", 1.0)),
            incoming_tokens=int(item.get("incoming_tokens", 0)),
            memory_blocks=item.get("memory_blocks", []),
            oom_triggered=bool(item.get("oom_triggered", False)),
            message=str(item.get("message", "")),
            done=bool(item.get("done", False)),
            reward=float(item.get("reward", 0.0)),
        )
    raise TypeError(f"Unsupported trajectory element type: {type(item)}")


def _validate_trajectory(trajectory: Sequence[Any]) -> None:
    if len(trajectory) > MAX_GRADER_TRAJECTORY_LEN:
        raise HTTPException(
            status_code=413,
            detail=f"Trajectory too long; max {MAX_GRADER_TRAJECTORY_LEN} items",
        )


@app.post("/grader")
def grader_endpoint(req: GraderRequest) -> dict[str, float]:
    if req.task_id not in SUPPORTED_TASKS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported task_id '{req.task_id}'. Use one of: easy, medium, hard.",
        )
    _validate_trajectory(req.trajectory)
    graders = {"easy": grader_easy, "medium": grader_medium, "hard": grader_hard}
    grader_fn = graders[req.task_id]
    try:
        trajectory = [_to_observation(item) for item in req.trajectory]
        score = grader_fn(trajectory)
        return {"score": float(max(0.01, min(0.99, score)))}
    except HTTPException:
        raise
    except (TypeError, ValueError) as e:
        logger.warning("/grader rejected invalid payload for task '%s': %s", req.task_id, e)
        raise HTTPException(status_code=422, detail="Invalid trajectory payload") from e
    except Exception as e:
        logger.error("/grader failed for task '%s': %s", req.task_id, e, exc_info=True)
        return {"score": 0.01}


@app.post("/baseline")
def baseline_endpoint() -> dict[str, float]:
    results: dict[str, float] = {}
    for task_name in ["easy", "medium", "hard"]:
        try:
            results[task_name] = float(_run_baseline_episode(task_name))
        except Exception as e:
            logger.error("Baseline failed for task '%s': %s", task_name, e, exc_info=True)
            results[task_name] = 0.01
    return results


def _run_baseline_episode(task_name: str) -> float:
    env = ContextRouterEnv()
    env.set_task(task_name)
    first_obs = env.reset(seed=42)

    initial_blocks = list(first_obs.memory_blocks)
    protected_ids = _protected_block_ids(initial_blocks)
    trajectory: list[CacheObservation] = []

    for _ in range(BASELINE_MAX_STEPS[task_name]):
        if not env._blocks:
            break

        total_tokens = sum(block.token_count for block in env._blocks.values())
        utilization = total_tokens / max(1, env._max_capacity)
        target_block_id, tactic = _baseline_action_for_state(
            task_name=task_name,
            blocks=env._blocks,
            protected_ids=protected_ids,
            utilization=utilization,
        )

        block = env._blocks[target_block_id]
        priority = _hard_priority_from_block(block) if task_name == "hard" else None

        obs = env.step(
            CacheAction(
                target_block_id=target_block_id,
                tactic=tactic,
                priority=priority,
            )
        )
        trajectory.append(obs)
        if obs.done:
            break

    grader_fn = {"easy": grader_easy, "medium": grader_medium, "hard": grader_hard}[task_name]
    return grader_fn(trajectory)


def _protected_block_ids(blocks: list[Any]) -> set[int]:
    protected_ids: set[int] = set()
    for block in blocks:
        block_id = int(getattr(block, "block_id", -1))
        block_type = str(getattr(block, "block_type", ""))
        attention = float(getattr(block, "attention_score", 0.0))
        if block_id < 0:
            continue
        if block_type == "system_prompt" or attention >= 0.55:
            protected_ids.add(block_id)
    return protected_ids


def _baseline_action_for_state(
    *,
    task_name: str,
    blocks: dict[int, Any],
    protected_ids: set[int],
    utilization: float,
) -> tuple[int, EvictionTactic]:
    all_ids = set(blocks.keys())
    def ranking_key(block_id: int) -> tuple[float, int, int]:
        block = blocks[block_id]
        attention = float(getattr(block, "attention_score", 0.0))
        age = int(getattr(block, "age", 0))
        tokens = int(getattr(block, "token_count", 0))
        return (attention, -age, -tokens)

    if task_name == "easy":
        target_block_id = max(all_ids, key=lambda block_id: int(getattr(blocks[block_id], "token_count", 0)))
        if utilization > 0.46:
            return target_block_id, EvictionTactic.EVICT
        return target_block_id, EvictionTactic.RETAIN

    candidate_ids = [block_id for block_id in all_ids if block_id not in protected_ids]
    if utilization > 0.65 or not candidate_ids:
        candidate_ids = list(all_ids)

    target_block_id = min(candidate_ids, key=ranking_key)
    target_block = blocks[target_block_id]
    target_tokens = int(getattr(target_block, "token_count", 0))

    if utilization > 0.80:
        return target_block_id, EvictionTactic.EVICT
    if utilization > 0.45:
        if target_tokens >= 300:
            return target_block_id, EvictionTactic.COMPRESS
        return target_block_id, EvictionTactic.EVICT
    return target_block_id, EvictionTactic.RETAIN


def _hard_priority_from_block(block: Any) -> int:
    score = 3
    block_type = getattr(block, "block_type", "")
    attention = float(getattr(block, "attention_score", 0.0))
    age = int(getattr(block, "age", 0))
    token_count = int(getattr(block, "token_count", 0))

    if block_type in {"system_prompt", "code_snippet"}:
        score += 1
    if attention >= 0.75:
        score += 1
    elif attention <= 0.25:
        score -= 1
    if age <= 2:
        score += 1
    elif age >= 12:
        score -= 1
    if token_count >= 700:
        score += 1
    elif token_count <= 150:
        score -= 1
    return max(1, min(5, score))


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # openenv validate expects this callable symbol.
    main()
