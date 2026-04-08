#!/usr/bin/env python3
import asyncio
import json
import os
from typing import Any, Optional

from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

ENV_SERVER_URL = os.getenv("ENV_SERVER_URL", "http://localhost:8000")
BENCHMARK = os.getenv("BENCHMARK", "context_router")
TASKS = [t.strip() for t in os.getenv("TASKS", "easy,medium,hard").split(",") if t.strip()]
MAX_STEPS = int(os.getenv("MAX_STEPS", "50"))
SUCCESS_SCORE_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.10"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "15"))

SYSTEM_PROMPT = (
    "You are a KV-cache memory manager. Return JSON only with keys "
    "target_block_id (int), tactic (evict|retain|compress), and optional priority (1-5)."
)


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def _fallback_action(obs: dict[str, Any]) -> dict[str, Any]:
    blocks = obs.get("memory_blocks", [])
    if not blocks:
        return {"target_block_id": 0, "tactic": "retain"}

    def rank(block: dict[str, Any]) -> tuple[float, int, int]:
        return (
            float(block.get("attention_score", 0.0)),
            -int(block.get("age", 0)),
            -int(block.get("token_count", 0)),
        )

    target = min(blocks, key=rank)
    target_id = int(target.get("block_id", 0))
    vram = float(obs.get("vram_utilization", 1.0))

    tactic = "evict"
    if vram < 0.40:
        tactic = "retain"
    elif int(target.get("token_count", 0)) >= 300 and vram >= 0.45:
        tactic = "compress"
    if target.get("block_type") == "system_prompt" and tactic == "evict":
        tactic = "retain"

    return {"target_block_id": target_id, "tactic": tactic}


def _call_llm(client: OpenAI, obs: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        user_prompt = json.dumps(obs, separators=(",", ":"), ensure_ascii=True)
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            timeout=LLM_TIMEOUT,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        action = json.loads(content)
        if "target_block_id" not in action or "tactic" not in action:
            return None
        if action["tactic"] not in {"evict", "retain", "compress"}:
            return None
        action["target_block_id"] = int(action["target_block_id"])
        if "priority" in action and action["priority"] is not None:
            action["priority"] = int(action["priority"])
        return action
    except Exception:
        return None


async def run_task(task_name: str, client: OpenAI) -> float:
    env = None
    rewards: list[float] = []
    steps_taken = 0
    score = 0.01
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        try:
            from context_router.client import MyEnv
            from context_router.models import CacheAction
            env = MyEnv(ENV_SERVER_URL)
        except ImportError:
            return 0.01

        try:
            result = await env.reset(task_name=task_name)
        except Exception:
            try:
                result = await env.reset()
            except Exception:
                log_step(step=1, action="{}", reward=0.00, done=True, error=None)
                return 0.01

        for step in range(1, MAX_STEPS + 1):
            if bool(result.done):
                break

            obs = result.observation.model_dump()
            action = _call_llm(client, obs) or _fallback_action(obs)
            action_str = json.dumps(action, separators=(",", ":"), ensure_ascii=True)

            reward = 0.0
            done = True
            err: Optional[str] = None

            try:
                result = await env.step(CacheAction(**action))
                reward = float(result.reward or 0.0)
                reward = max(0.0, min(1.0, reward))
                done = bool(result.done)
                obs_next = result.observation.model_dump()
                raw_error = obs_next.get("last_action_error")
                err = str(raw_error) if raw_error else None
            except Exception:
                done = True
                reward = 0.0
                err = None

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward, done=done, error=err)

            if done:
                break

        mean_reward = sum(rewards) / max(1, len(rewards))
        score = max(0.01, min(0.99, mean_reward))
        success = score >= SUCCESS_SCORE_THRESHOLD
        return score
    finally:
        try:
            if env is not None:
                await env.close()
        except Exception:
            pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main() -> int:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    for task in TASKS:
        await run_task(task_name=task, client=client)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
