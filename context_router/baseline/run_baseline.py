import sys
import time
import httpx
import asyncio
from typing import List, Dict

try:
    from context_router.client import MyEnv
    from context_router.models import CacheAction, EvictionTactic, CacheObservation
except ImportError:
    # If run as a script without module installation
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from context_router.client import MyEnv
    from context_router.models import CacheAction, EvictionTactic, CacheObservation

BASE_URL = "http://localhost:8000"

async def wait_for_server(url: str, max_retries: int = 5, delay: int = 2):
    """Wait for the FastAPI server to boot up and respond."""
    print(f"Waiting for server at {url}...")
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{url}/tasks")
                if r.status_code == 200:
                    print("Server is up and reachable!")
                    return
        except httpx.RequestError:
            pass
        print(f"  Attempt {i+1}/{max_retries} failed. Retrying in {delay}s...")
        await asyncio.sleep(delay)
    print("Error: Server did not respond. Exiting.")
    sys.exit(1)

async def run_task(task_id: str, env: MyEnv) -> float:
    """Run one episode of the environment as a naive baseline agent."""
    print(f"\n--- Running baseline for task: {task_id} ---")
    try:
        # Attempt to reset environment
        step_result = await env.reset()
        obs = step_result.observation
        done = False
        trajectory: List[Dict] = []
        
        step_count = 0
        while not done and step_count < 100:
            trajectory.append(obs if isinstance(obs, dict) else obs.model_dump())
            
            # Naive Baseline Strategy: ALWAYS COMPRESS OLDEST
            tactic = EvictionTactic.COMPRESS
            target_id = 0
            # obs might be a dict now from EnvClient
            blocks = obs.get("memory_blocks", []) if isinstance(obs, dict) else obs.memory_blocks
            if blocks:
                first_block = blocks[0]
                target_id = first_block.get("block_id", 0) if isinstance(first_block, dict) else first_block.block_id
                
            action = CacheAction(target_block_id=target_id, tactic=tactic)
            step_result = await env.step(action)
            obs = step_result.observation
            done = step_result.done
            step_count += 1
            
        trajectory.append(obs if isinstance(obs, dict) else obs.model_dump())
        print(f"Generated trajectory of {len(trajectory)} states.")
        
        # Submit trajectory to grader
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{BASE_URL}/grader", json={"task_id": task_id, "trajectory": trajectory})
            r.raise_for_status()
            score = r.json().get("score", 0.0)
            
        print(f"Score for {task_id}: {score}")
        return float(score)
        
    except httpx.HTTPError as e:
        print(f"HTTP Error during grading / interaction: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error in run_task: {e}")
        sys.exit(1)

async def main():
    # 1. Wait for server
    await wait_for_server(BASE_URL)
    
    # Initialize a single client connection to respect max_concurrent_envs=1
    env = MyEnv(BASE_URL)
    
    # 2. Run Baseline on all 3 tasks
    scores = {}
    for task_id in ["easy", "medium", "hard"]:
        scores[task_id] = await run_task(task_id, env)
        
    print("\n==============================")
    print("FINAL BASELINE EVALUATION SCORES")
    print("==============================")
    for t_id, s in scores.items():
        print(f"{t_id.capitalize():<10}: {s:.4f}")
        
    # 4. Exit successfully
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
