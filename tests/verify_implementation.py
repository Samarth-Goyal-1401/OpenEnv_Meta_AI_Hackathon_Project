import sys
import os
from pathlib import Path

print("1. Starting verification script")
# Add the context_router directory to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "context_router"))
print(f"2. PYTHONPATH updated: {sys.path[0]}")

try:
    print("3. Importing models...")
    from models import CacheObservation, CacheAction, EvictionTactic, MemoryBlockInfo
    print("✓ models imported")
    
    print("4. Importing graders...")
    from graders.grader_easy import grader_easy
    from graders.grader_medium import grader_medium
    from graders.grader_hard import grader_hard
    print("✓ graders imported")
    
    print("5. Importing ContextRouterEnv...")
    from server.context_env import ContextRouterEnv
    print("✓ ContextRouterEnv imported")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

def _test():
    print("6. Initializing Environment...")
    env = ContextRouterEnv()
    print("✓ Env initialized")
    
    print("7. Setting task 'easy'...")
    env.set_task("easy")
    print("✓ task set")
    
    print("8. Resetting env...")
    obs = env.reset(seed=42)
    print(f"✓ reset ok. VRAM: {obs.vram_utilization}")
    
    print("9. Running easy test...")
    traj = [obs] * 10
    score = grader_easy(traj)
    print(f"  Easy score: {score:.4f}")
    
    print("\n✓ ALL LOCAL LOGIC CHECKS PASSED")

if __name__ == "__main__":
    _test()
