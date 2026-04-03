#!/usr/bin/env python3
"""
inference.py — Root-level LLM inference script for the Edge GPU Context Router.

MANDATORY HACKATHON REQUIREMENTS:
  1. Uses the official `openai` Python package.
  2. Reads API_BASE_URL, MODEL_NAME, HF_TOKEN from environment.
  3. Emits structured stdout logs: [START], [STEP], [END].
  4. Falls back to heuristic action if LLM fails or times out.
  5. Runtime < 20 minutes on vcpu=2, memory=8gb.
"""

import json
import os
import random
import sys
import time

import httpx
from openai import OpenAI

# ── Configuration ────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Where our OpenEnv server is running
ENV_SERVER_URL = os.environ.get("ENV_SERVER_URL", "http://localhost:8000")

# Timeouts
LLM_TIMEOUT = 15  # seconds per LLM call
MAX_STEPS_PER_TASK = 50
TASKS = ["easy", "medium", "hard"]

# ── OpenAI Client ────────────────────────────────────────────────────────────
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or "no-key-provided",
)

SYSTEM_PROMPT = """You are an expert Edge GPU memory manager. You manage KV-cache blocks for a local LLM running on limited VRAM.

Given the current observation (JSON), you must decide which memory block to act on and what tactic to use.

Available tactics:
- "evict": Remove the block entirely, freeing its tokens.
- "retain": Keep the block as-is.
- "compress": Halve the block's token count (only for medium/hard tasks).

Strategy:
- Evict blocks with LOW attention_score and HIGH age first.
- NEVER evict system_prompt blocks — they are critical.
- If VRAM utilisation is high (>0.7), prefer evicting to free space.
- If VRAM is moderate (0.4-0.7), compress large low-attention blocks.
- If VRAM is low (<0.4), retain everything.

Respond with ONLY a JSON object, no markdown, no explanation:
{"target_block_id": <int>, "tactic": "<evict|retain|compress>", "priority": <int 1-5 or null>}
"""


def _build_user_prompt(task_id: str, obs: dict) -> str:
    """Build a user prompt from the observation."""
    blocks_summary = []
    for b in obs.get("memory_blocks", []):
        blocks_summary.append(
            f"  Block {b['block_id']}: type={b['block_type']}, "
            f"attention={b['attention_score']:.3f}, "
            f"tokens={b['token_count']}, age={b['age']}"
        )
    blocks_str = "\n".join(blocks_summary) if blocks_summary else "  (no blocks)"

    return (
        f"Task: {task_id}\n"
        f"VRAM Utilisation: {obs.get('vram_utilization', 1.0):.3f}\n"
        f"Incoming Tokens: {obs.get('incoming_tokens', 0)}\n"
        f"OOM Triggered: {obs.get('oom_triggered', False)}\n"
        f"Memory Blocks:\n{blocks_str}\n\n"
        f"Return your action as JSON."
    )


def _call_llm(task_id: str, obs: dict) -> dict | None:
    """Call the LLM via OpenAI client. Returns parsed action dict or None on failure."""
    try:
        user_prompt = _build_user_prompt(task_id, obs)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=100,
            timeout=LLM_TIMEOUT,
        )
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        action = json.loads(content)

        # Validate required fields
        if "target_block_id" not in action or "tactic" not in action:
            return None
        if action["tactic"] not in ("evict", "retain", "compress"):
            return None
        # Easy task: no compress allowed
        if task_id == "easy" and action["tactic"] == "compress":
            action["tactic"] = "evict"

        return action
    except Exception:
        return None


def _fallback_action(task_id: str, obs: dict) -> dict:
    """Heuristic fallback when LLM fails — mirrors the baseline strategy."""
    blocks = obs.get("memory_blocks", [])
    if not blocks:
        return {"target_block_id": 0, "tactic": "retain"}

    utilization = obs.get("vram_utilization", 1.0)

    # Build block map
    block_map = {}
    for b in blocks:
        try:
            bid = int(b.get("block_id", -1))
            if bid >= 0:
                block_map[bid] = b
        except (TypeError, ValueError):
            continue

    if not block_map:
        return {"target_block_id": 0, "tactic": "retain"}

    # Protect system_prompt and high-attention blocks
    protected = set()
    for bid, b in block_map.items():
        if b.get("block_type") == "system_prompt" or float(b.get("attention_score", 0)) >= 0.55:
            protected.add(bid)

    if task_id == "easy":
        # Evict the largest non-system block
        target = max(
            block_map.keys(),
            key=lambda bid: int(block_map[bid].get("token_count", 0)),
        )
        tactic = "evict" if utilization > 0.46 else "retain"
        return {"target_block_id": target, "tactic": tactic}

    # Medium/Hard — ranking by lowest attention, highest age, most tokens
    candidates = [bid for bid in block_map if bid not in protected]
    if utilization > 0.65 or not candidates:
        candidates = list(block_map.keys())

    def rank(bid):
        b = block_map[bid]
        return (float(b.get("attention_score", 0)), -int(b.get("age", 0)), -int(b.get("token_count", 0)))

    target = min(candidates, key=rank)
    target_tokens = int(block_map[target].get("token_count", 0))

    if utilization > 0.80:
        tactic = "evict"
    elif utilization > 0.45:
        tactic = "compress" if target_tokens >= 300 else "evict"
    else:
        tactic = "retain"

    action = {"target_block_id": target, "tactic": tactic}

    # Hard task: compute priority
    if task_id == "hard":
        b = block_map[target]
        score = 3
        if b.get("block_type") in ("system_prompt", "code_snippet"):
            score += 1
        attn = float(b.get("attention_score", 0))
        if attn >= 0.75:
            score += 1
        elif attn <= 0.25:
            score -= 1
        age = int(b.get("age", 0))
        if age <= 2:
            score += 1
        elif age >= 12:
            score -= 1
        tc = int(b.get("token_count", 0))
        if tc >= 700:
            score += 1
        elif tc <= 150:
            score -= 1
        action["priority"] = max(1, min(5, score))

    return action


def _env_request(method: str, path: str, json_data: dict | None = None) -> dict:
    """Make an HTTP request to the OpenEnv server."""
    url = f"{ENV_SERVER_URL}{path}"
    with httpx.Client(timeout=30, trust_env=False) as http:
        if method == "GET":
            resp = http.get(url)
        else:
            resp = http.post(url, json=json_data or {})
        resp.raise_for_status()
        return resp.json()


def run_task(task_id: str) -> float:
    """Run one task episode and emit structured [START]/[STEP]/[END] logs."""
    print(f"[START] Task: {task_id}")

    try:
        # Reset the environment
        reset_resp = _env_request("POST", "/reset")
        obs = reset_resp.get("observation", reset_resp)
        done = reset_resp.get("done", False)
    except Exception as e:
        print(f"[STEP] Step: 1, Action: {{}}, Reward: 0.0")
        print(f"[END] Score: 0.0")
        return 0.0

    cumulative_reward = 0.0
    step_num = 0

    for i in range(MAX_STEPS_PER_TASK):
        if done:
            break

        step_num = i + 1

        # Try LLM first, fallback to heuristic
        action = _call_llm(task_id, obs)
        if action is None:
            action = _fallback_action(task_id, obs)

        action_json_str = json.dumps(action)

        try:
            # OpenEnv framework expects {"action": {...}}
            step_resp = _env_request("POST", "/step", json_data={"action": action})
            obs = step_resp.get("observation", step_resp)
            reward = float(step_resp.get("reward", 0.0))
            done = bool(step_resp.get("done", False))
        except Exception:
            reward = 0.0
            done = True

        cumulative_reward += reward
        print(f"[STEP] Step: {step_num}, Action: {action_json_str}, Reward: {reward}")

    # Compute final score as average reward
    final_score = cumulative_reward / max(1, step_num)
    final_score = max(0.0, min(1.0, final_score))

    print(f"[END] Score: {final_score}")
    return final_score


def main() -> int:
    """Run all tasks and report scores."""
    all_scores: dict[str, float] = {}

    for task_id in TASKS:
        try:
            score = run_task(task_id)
            all_scores[task_id] = score
        except Exception:
            print(f"[END] Score: 0.0")
            all_scores[task_id] = 0.0

    # Summary
    print("\n--- Final Scores ---")
    for task_id, score in all_scores.items():
        print(f"  {task_id}: {score:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
