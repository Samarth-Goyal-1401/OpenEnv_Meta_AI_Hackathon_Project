import sys
from pathlib import Path

print("1. Starting verification script")
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "context_router"))
print(f"2. PYTHONPATH updated: {sys.path[0]}")

try:
    print("3. Importing models...")
    from models import CacheAction, CacheObservation, EvictionTactic, MemoryBlockInfo

    print("[OK] models imported")

    print("4. Importing graders...")
    from graders.grader_easy import grader_easy
    from graders.grader_hard import grader_hard
    from graders.grader_medium import grader_medium

    print("[OK] graders imported")

    print("5. Importing ContextRouterEnv...")
    from server.context_env import ContextRouterEnv

    print("[OK] ContextRouterEnv imported")
except ImportError as error:
    print(f"[FAIL] Import failed: {error}")
    sys.exit(1)


def _score_for_task(task_name: str) -> float:
    env = ContextRouterEnv()
    env.set_task(task_name)
    observation = env.reset(seed=42)
    if observation.done:
        raise AssertionError(f"{task_name}: reset should not be done")
    if not observation.memory_blocks:
        raise AssertionError(f"{task_name}: reset returned no memory blocks")

    trajectory = [observation]
    max_steps = 8

    for _ in range(max_steps):
        if not observation.memory_blocks or observation.done:
            break

        target_id = observation.memory_blocks[0].block_id
        if task_name == "easy":
            action = CacheAction(
                target_block_id=target_id,
                tactic=EvictionTactic.EVICT,
            )
        elif task_name == "medium":
            action = CacheAction(
                target_block_id=target_id,
                tactic=EvictionTactic.COMPRESS,
            )
        else:
            action = CacheAction(
                target_block_id=target_id,
                tactic=EvictionTactic.COMPRESS,
                priority=3,
            )

        observation = env.step(action)
        trajectory.append(observation)

    if task_name == "easy":
        score = grader_easy(trajectory)
    elif task_name == "medium":
        score = grader_medium(trajectory)
    else:
        score = grader_hard(trajectory)

    if not 0.0 <= score <= 1.0:
        raise AssertionError(f"{task_name}: grader returned out-of-range score {score}")
    return score


def _test() -> None:
    print("6. Running task-level smoke checks...")
    scores = {
        "easy": _score_for_task("easy"),
        "medium": _score_for_task("medium"),
        "hard": _score_for_task("hard"),
    }
    print("7. Grader score ranges verified (0..1):")
    print(f"  Easy:   {scores['easy']:.4f}")
    print(f"  Medium: {scores['medium']:.4f}")
    print(f"  Hard:   {scores['hard']:.4f}")

    print("\n[OK] LOCAL IMPLEMENTATION SMOKE CHECKS PASSED")


if __name__ == "__main__":
    _test()
