import os
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


def _test() -> None:
    print("6. Initializing Environment...")
    env = ContextRouterEnv()
    print("[OK] Env initialized")

    print("7. Setting task 'easy'...")
    env.set_task("easy")
    print("[OK] task set")

    print("8. Resetting env...")
    observation = env.reset(seed=42)
    print(f"[OK] reset ok. VRAM: {observation.vram_utilization}")

    print("9. Running easy test...")
    trajectory = [observation] * 10
    score = grader_easy(trajectory)
    print(f"  Easy score: {score:.4f}")

    print("\n[OK] ALL LOCAL LOGIC CHECKS PASSED")


if __name__ == "__main__":
    _test()
