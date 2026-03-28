import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from context_router.models import CacheAction, CacheObservation, EvictionTactic
from context_router.server.context_env import ContextRouterEnv
from context_router.graders.grader_easy import grader_easy

def test_integration():
    env = ContextRouterEnv()
    
    # 1. Reset
    obs = env.reset(seed=42)
    print("Initial Obs VRAM:", obs.vram_utilization)
    assert obs.vram_utilization > 0
    assert not obs.done
    
    # 2. Simulate short trajectory
    trajectory = [obs]
    
    for i in range(3):
        if not obs.memory_blocks:
            break
        act = CacheAction(target_block_id=obs.memory_blocks[0].block_id, tactic=EvictionTactic.EVICT)
        obs = env.step(act)
        trajectory.append(obs)
        if obs.done:
            break
            
    # 3. Grader check
    score = grader_easy(trajectory)
    print(f"Integration Check passed! Evaluated score for easy grader: {score}")

if __name__ == "__main__":
    test_integration()
