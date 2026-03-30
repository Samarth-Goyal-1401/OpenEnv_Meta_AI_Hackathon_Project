import logging
import random
from typing import Any

from openenv.core.env_server import create_app
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


# RULEBOOK PB1: pass the environment class, never an instance.
app = create_app(ContextRouterEnv, CacheAction, CacheObservation, env_name="context_router")


class GraderRequest(BaseModel):
    task_id: str = Field(..., description="Task id: easy | medium | hard")
    trajectory: list[Any] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks() -> dict[str, list[dict[str, Any]]]:
    return {"tasks": list(TASKS.values())}


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


@app.post("/grader")
def grader_endpoint(req: GraderRequest) -> dict[str, float]:
    graders = {"easy": grader_easy, "medium": grader_medium, "hard": grader_hard}
    grader_fn = graders.get(req.task_id, grader_easy)
    try:
        trajectory = [_to_observation(item) for item in req.trajectory]
        score = grader_fn(trajectory)
        return {"score": float(max(0.0, min(1.0, score)))}
    except Exception as e:
        logger.error("/grader failed for task '%s': %s", req.task_id, e, exc_info=True)
        return {"score": 0.0}


@app.post("/baseline")
def baseline_endpoint() -> dict[str, float]:
    results: dict[str, float] = {}
    for task_name in ["easy", "medium", "hard"]:
        try:
            results[task_name] = float(_run_baseline_episode(task_name))
        except Exception as e:
            logger.error("Baseline failed for task '%s': %s", task_name, e, exc_info=True)
            results[task_name] = 0.0
    return results


def _run_baseline_episode(task_name: str) -> float:
    env = ContextRouterEnv()
    env.set_task(task_name)
    env.reset(seed=42)

    rng = random.Random(42)
    trajectory: list[CacheObservation] = []

    for _ in range(10):
        if not env._blocks:
            break

        target_block_id = rng.choice(list(env._blocks.keys()))
        if task_name == "easy":
            tactic = rng.choice([EvictionTactic.EVICT, EvictionTactic.RETAIN])
        else:
            tactic = rng.choice(
                [EvictionTactic.EVICT, EvictionTactic.RETAIN, EvictionTactic.COMPRESS]
            )
        priority = None
        if task_name == "hard":
            block = env._blocks[target_block_id]
            priority = _hard_priority_from_block(block)

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
