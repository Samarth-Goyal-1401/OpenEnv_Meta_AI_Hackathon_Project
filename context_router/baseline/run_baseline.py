#!/usr/bin/env python3
import argparse
import asyncio
import sys
from typing import Any

import httpx

try:
    from context_router.client import MyEnv
    from context_router.models import CacheAction, EvictionTactic
except ImportError:
    import os

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from context_router.client import MyEnv
    from context_router.models import CacheAction, EvictionTactic


async def wait_for_server(base_url: str, retries: int = 10, delay_seconds: int = 2) -> bool:
    for _ in range(retries):
        try:
            async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                response = await client.get(f"{base_url}/tasks")
                if response.status_code == 200:
                    return True
        except httpx.HTTPError:
            pass
        await asyncio.sleep(delay_seconds)
    return False


async def fetch_server_baseline(base_url: str) -> dict[str, float] | None:
    """
    Prefer the server baseline endpoint for Phase 3 smoke checks.
    This evaluates easy/medium/hard with the server's canonical behavior.
    """
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            response = await client.post(f"{base_url}/baseline")
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            return None
        return {
            "easy": float(payload.get("easy", 0.01)),
            "medium": float(payload.get("medium", 0.01)),
            "hard": float(payload.get("hard", 0.01)),
        }
    except Exception:
        return None


def _extract_blocks(obs: Any) -> list[dict[str, Any]]:
    if isinstance(obs, dict):
        return obs.get("memory_blocks", [])
    blocks = getattr(obs, "memory_blocks", [])
    if isinstance(blocks, list):
        return [b.model_dump() if hasattr(b, "model_dump") else b for b in blocks]
    return []


def _obs_to_dict(obs: Any) -> dict[str, Any]:
    if isinstance(obs, dict):
        return obs
    if hasattr(obs, "model_dump"):
        return obs.model_dump()
    return {
        "vram_utilization": 1.0,
        "incoming_tokens": 0,
        "memory_blocks": [],
        "oom_triggered": False,
        "message": "invalid observation format",
        "done": True,
        "reward": 0.0,
    }


def _hard_priority_from_block(block: dict[str, Any]) -> int:
    score = 3
    block_type = str(block.get("block_type", ""))
    attention = float(block.get("attention_score", 0.0))
    age = int(block.get("age", 0))
    token_count = int(block.get("token_count", 0))

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


def _protected_ids_from_initial(blocks: list[dict[str, Any]]) -> set[int]:
    protected: set[int] = set()
    for block in blocks:
        try:
            block_id = int(block.get("block_id", -1))
        except (TypeError, ValueError):
            continue
        if block_id < 0:
            continue
        block_type = str(block.get("block_type", ""))
        attention = float(block.get("attention_score", 0.0))
        if block_type == "system_prompt" or attention >= 0.55:
            protected.add(block_id)
    return protected


def _choose_action(
    task_id: str,
    blocks: list[dict[str, Any]],
    protected_ids: set[int],
    utilization: float,
) -> tuple[int, EvictionTactic]:
    if not blocks:
        return 0, EvictionTactic.RETAIN

    block_map: dict[int, dict[str, Any]] = {}
    for block in blocks:
        try:
            block_id = int(block.get("block_id", -1))
        except (TypeError, ValueError):
            continue
        if block_id >= 0:
            block_map[block_id] = block
    if not block_map:
        return 0, EvictionTactic.RETAIN

    def ranking_key(block_id: int) -> tuple[float, int, int]:
        block = block_map[block_id]
        attention = float(block.get("attention_score", 0.0))
        age = int(block.get("age", 0))
        tokens = int(block.get("token_count", 0))
        return (attention, -age, -tokens)

    if task_id == "easy":
        target = max(block_map.keys(), key=lambda block_id: int(block_map[block_id].get("token_count", 0)))
        if utilization > 0.46:
            return target, EvictionTactic.EVICT
        return target, EvictionTactic.RETAIN

    candidate_ids = [block_id for block_id in block_map if block_id not in protected_ids]
    if utilization > 0.65 or not candidate_ids:
        candidate_ids = list(block_map.keys())

    target = min(candidate_ids, key=ranking_key)
    target_tokens = int(block_map[target].get("token_count", 0))

    if utilization > 0.80:
        return target, EvictionTactic.EVICT
    if utilization > 0.45:
        if target_tokens >= 300:
            return target, EvictionTactic.COMPRESS
        return target, EvictionTactic.EVICT
    return target, EvictionTactic.RETAIN


async def run_task(base_url: str, task_id: str, env: MyEnv) -> float:
    try:
        step_result = await env.reset()
        obs = step_result.observation
        done = bool(step_result.done)
        trajectory: list[dict[str, Any]] = []
        initial_blocks = _extract_blocks(obs)
        protected_ids = _protected_ids_from_initial(initial_blocks)

        max_steps = 7 if task_id == "hard" else 50
        for _ in range(max_steps):
            trajectory.append(_obs_to_dict(obs))
            if done:
                break

            blocks = _extract_blocks(obs)
            utilization = float(_obs_to_dict(obs).get("vram_utilization", 1.0))
            target, tactic = _choose_action(task_id, blocks, protected_ids, utilization)

            if task_id == "hard" and blocks:
                selected = blocks[0]
                for block in blocks:
                    try:
                        block_id = int(block.get("block_id", -1))
                    except (TypeError, ValueError):
                        continue
                    if block_id == target:
                        selected = block
                        break
                priority = _hard_priority_from_block(selected)
                action = CacheAction(
                    target_block_id=target, tactic=tactic, priority=priority
                )
            else:
                action = CacheAction(target_block_id=target, tactic=tactic)
            step_result = await env.step(action)
            obs = step_result.observation
            done = bool(step_result.done)

        trajectory.append(_obs_to_dict(obs))

        payload = {"task_id": task_id, "trajectory": trajectory}
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            response = await client.post(f"{base_url}/grader", json=payload)
            response.raise_for_status()
            score = float(response.json().get("score", 0.0))
        return float(max(0.01, min(0.99, score)))
    except Exception:
        return 0.01


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run baseline evaluation for Context Router")
    parser.add_argument("--base-url", required=True, help="Base URL of the environment server")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    server_ready = await wait_for_server(base_url)
    if not server_ready:
        print("Task easy score:   0.0100")
        print("Task medium score: 0.0100")
        print("Task hard score:   0.0100")
        return 0

    scores = await fetch_server_baseline(base_url)
    if scores is None:
        env = MyEnv(base_url)
        scores = {}
        for task_id in ["easy", "medium", "hard"]:
            scores[task_id] = await run_task(base_url, task_id, env)

    print(f"Task easy score:   {scores['easy']:.4f}")
    print(f"Task medium score: {scores['medium']:.4f}")
    print(f"Task hard score:   {scores['hard']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
