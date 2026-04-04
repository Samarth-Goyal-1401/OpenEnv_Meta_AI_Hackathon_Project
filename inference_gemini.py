#!/usr/bin/env python3
import json
import os
import random
import sys
import time

import httpx
from openai import OpenAI

API_BASE_URL = os.environ.get('API_BASE_URL', 'https://api.openai.com/v1')
MODEL_NAME = os.environ.get('MODEL_NAME', 'gpt-4o-mini') # Updated default to the official Meta OpenEnv model
HF_TOKEN = os.environ.get('HF_TOKEN') or os.environ.get('OPENAI_API_KEY', '')
ENV_SERVER_URL = os.environ.get('ENV_SERVER_URL', 'http://localhost:8000')

LLM_TIMEOUT = 15
MAX_STEPS_PER_TASK = 50
TASKS = ['easy', 'medium', 'hard']

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or 'no-key-provided')

SYSTEM_PROMPT = """You are a KV-cache memory management agent. Your goal is to prevent Out-of-Memory (OOM) events by choosing the optimal memory tactic for one block per step.

=======================================================
CRITICAL RULE - READ THIS FIRST
=======================================================
If the LAST_ACTION reward was 0.0, that action was REJECTED by the environment.
A reward of 0.0 is NOT "low reward" - it means the action was INVALID and had NO effect.
You MUST choose a DIFFERENT block or a DIFFERENT tactic next step.
NEVER repeat the same (block_id, tactic) pair that just returned 0.0.
Repeating a rejected action wastes your entire step budget.

=======================================================
INPUTS (provided each step)
=======================================================
VRAM_UTILIZATION   : float (0.0-1.0)
BLOCKS             : list of objects:
  - id             : int
  - type           : str   ("system_prompt" | "code_snippet" | "rag_context" | "small_talk" | "conversation" | other)
  - attention_score: float (0.0-1.0)   higher = more critical
  - age_steps      : int               steps since last access; higher = staler
  - token_count    : int
  - compressed     : bool              True = already halved; compress is INVALID on this block
LAST_ACTION        : object:
  - block_id       : int
  - tactic         : str
  - reward         : float             0.0 = REJECTED. Positive = success.

=======================================================
TACTIC ELIGIBILITY  (check BEFORE choosing)
=======================================================
"evict"
  Removed block entirely. Highest VRAM relief.
  FORBIDDEN on: system_prompt, code_snippet  (unless VRAM > 0.97)
  PREFER on: type in {small_talk, rag_context}, attention_score < 0.25, age_steps > 500

"compress"
  Halves token count. Moderate VRAM relief.
  FORBIDDEN when: block.compressed == True  (this causes reward = 0.0 every time)
  FORBIDDEN when: token_count <= 300
  If compress returns 0.0, that block is ALREADY COMPRESSED - evict it instead if needed

"retain"
  No-op. Signals block should stay.
  FORBIDDEN when: VRAM_UTILIZATION >= 0.90
  Useful for: system_prompt, code_snippet, attention_score > 0.80 when VRAM is safe

=======================================================
STEP-BY-STEP DECISION PROCESS
=======================================================
BEFORE CHOOSING, answer these questions silently:

  Q1. Did LAST_ACTION.reward == 0.0?
        YES -> That (block_id, tactic) is permanently blacklisted this episode.
              If tactic was "compress": mark that block as compressed. Do NOT try compress on it again.
              Choose a COMPLETELY DIFFERENT block and/or tactic now.
        NO  -> Continue.

  Q2. Is VRAM_UTILIZATION >= 0.90?
        YES -> retain is FORBIDDEN. You MUST evict or compress something.
        NO  -> All tactics are available (subject to eligibility).

  Q3. Which blocks are eligible for each tactic?
        For evict    : all blocks except system_prompt and code_snippet (unless VRAM > 0.97)
        For compress : blocks where compressed == False AND token_count > 300
        For retain   : any block (when VRAM < 0.90)

  Q4. Score each eligible block by urgency:
        urgency = (age_steps / 1000) + (1.0 - attention_score) + type_bonus
        type_bonus = 0.5 if type in {small_talk, rag_context}, else 0.0

  Q5. Apply tactic based on VRAM pressure:
        VRAM > 0.90 -> evict the highest-urgency eligible block
        VRAM > 0.85 -> evict OR compress; prefer evict for urgency > 0.7
        VRAM <= 0.85 -> compress medium-urgency blocks; retain critical ones

=======================================================
PRIORITY FIELD
=======================================================
5 = Protecting a critical block (retain on system_prompt / code_snippet)
4 = Evicting junk under high VRAM pressure (small_talk / rag_context, VRAM > 0.85)
3 = Compressing a medium-value block
2 = Evicting a low-attention non-critical block under medium pressure
1 = Retaining a non-critical block when VRAM is comfortable

=======================================================
OUTPUT  (strict JSON, no other text)
=======================================================
{"target_block_id": <int>, "tactic": "<evict|retain|compress>", "priority": <int 1-5>}

Final check before outputting:
  - Is this the same (block_id, tactic) that just returned 0.0? If yes, CHANGE IT.
  - Does the block.compressed == True and tactic == "compress"? If yes, CHANGE IT.
  - Is VRAM >= 0.90 and tactic == "retain"? If yes, CHANGE IT.
"""


def _build_user_prompt(task_id: str, obs: dict, history: list[dict]) -> str:
    blocks = obs.get('memory_blocks', [])

    compressed_ids = set()
    for h in history:
        if h.get('tactic') == 'compress':
            compressed_ids.add(h.get('block_id'))

    def urgency(b: dict) -> float:
        type_bonus = 0.5 if b.get('block_type') in ('small_talk', 'rag_context', 'priority_spill', 'hallucination_spill') else 0.0
        return (1.0 - float(b.get('attention_score', 0))) + (int(b.get('age', 0)) / 100.0) + type_bonus

    sorted_blocks = sorted(blocks, key=urgency, reverse=True)

    blocks_summary = []
    for b in sorted_blocks:
        bid = b['block_id']
        compressed_flag = ' [ALREADY COMPRESSED - do NOT compress again]' if bid in compressed_ids else ''
        blocks_summary.append(
            f"  Block {bid}: type={b['block_type']}, "
            f"attention={b['attention_score']:.3f}, "
            f"tokens={b['token_count']}, age={b['age']}"
            f"{compressed_flag}"
        )
    blocks_str = '\n'.join(blocks_summary) if blocks_summary else '  (no blocks)'

    if history:
        history_lines = [
            f"  Step -{len(history)-i}: block={h['block_id']}, tactic={h['tactic']}, reward={h['reward']:.4f}"
            for i, h in enumerate(history)
        ]
        history_str = '\n'.join(history_lines)
    else:
        history_str = '  (no previous actions)'

    last = history[-1] if history else None
    last_action_str = (
        f"block_id={last['block_id']}, tactic={last['tactic']}, reward={last['reward']:.4f}"
        if last else 'N/A'
    )

    return (
        f"Task: {task_id}\n"
        f"VRAM Utilisation: {obs.get('vram_utilization', 1.0):.3f}\n"
        f"Incoming Tokens: {obs.get('incoming_tokens', 0)}\n"
        f"OOM Triggered: {obs.get('oom_triggered', False)}\n"
        f"Environment Feedback (last step): {obs.get('message', 'None')}\n"
        f"LAST_ACTION: {last_action_str}\n"
        f"\nRecent Action History (newest first):\n{history_str}\n"
        f"\nMemory Blocks (sorted by eviction urgency - TOP = most deletable):\n{blocks_str}\n\n"
        f"Return your action as JSON."
    )

def _call_llm(task_id: str, obs: dict, history: list[dict]) -> dict | None:
    try:
        user_prompt = _build_user_prompt(task_id, obs, history)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=0.1,
            timeout=LLM_TIMEOUT,
            response_format={'type': 'json_object'},
        )
        content = response.choices[0].message.content or ""
        content = content.strip()

        # Strip markdown code blocks if the model insists on adding them
        if content.startswith("```"):
            lines = content.split('\n')
            if len(lines) > 1:
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()

        try:
            action = json.loads(content)
        except json.JSONDecodeError as je:
            print(f"JSON ERROR! Raw model output was: {repr(content)}")
            return None

        if 'target_block_id' not in action or 'tactic' not in action:
            return None
        if action['tactic'] not in ('evict', 'retain', 'compress'):
            return None
        if task_id == 'easy' and action['tactic'] == 'compress':
            action['tactic'] = 'evict'

        return action
    except Exception as e:
        print(f"LLM ERROR: {e}")
        return None

def _fallback_action(task_id: str, obs: dict) -> dict:
    blocks = obs.get('memory_blocks', [])
    if not blocks:
        return {'target_block_id': 0, 'tactic': 'retain'}

    utilization = obs.get('vram_utilization', 1.0)
    block_map = {}
    for b in blocks:
        try:
            bid = int(b.get('block_id', -1))
            if bid >= 0:
                block_map[bid] = b
        except (TypeError, ValueError):
            continue

    if not block_map:
        return {'target_block_id': 0, 'tactic': 'retain'}

    protected = set()
    for bid, b in block_map.items():
        if b.get('block_type') == 'system_prompt' or float(b.get('attention_score', 0)) >= 0.55:
            protected.add(bid)

    if task_id == 'easy':
        target = max(
            block_map.keys(),
            key=lambda bid: int(block_map[bid].get('token_count', 0)),
        )
        tactic = 'evict' if utilization > 0.46 else 'retain'
        return {'target_block_id': target, 'tactic': tactic}

    candidates = [bid for bid in block_map if bid not in protected]
    if utilization > 0.65 or not candidates:
        candidates = list(block_map.keys())

    def rank(bid):
        b = block_map[bid]
        return (float(b.get('attention_score', 0)), -int(b.get('age', 0)), -int(b.get('token_count', 0)))

    target = min(candidates, key=rank)
    target_tokens = int(block_map[target].get('token_count', 0))

    if utilization > 0.80:
        tactic = 'evict'
    elif utilization > 0.45:
        tactic = 'compress' if target_tokens >= 300 else 'evict'
    else:
        tactic = 'retain'

    action = {'target_block_id': target, 'tactic': tactic}
    if task_id == 'hard':
        b = block_map[target]
        score = 3
        if b.get('block_type') in ('system_prompt', 'code_snippet'):
            score += 1
        attn = float(b.get('attention_score', 0))
        if attn >= 0.75:
            score += 1
        elif attn <= 0.25:
            score -= 1
        age = int(b.get('age', 0))
        if age <= 2:
            score += 1
        elif age >= 12:
            score -= 1
        tc = int(b.get('token_count', 0))
        if tc >= 700:
            score += 1
        elif tc <= 150:
            score -= 1
        action['priority'] = max(1, min(5, score))

    return action

async def run_task(task_id: str, env) -> float:
    print(f"[START] Task: {task_id}")
    try:
        step_result = await env.reset()
        obs = step_result.observation.model_dump()
        done = step_result.done
    except Exception as e:
        print(f"[STEP] Step: 1, Action: {{}}, Reward: 0.0")
        print(f"[END] Score: 0.0")
        return 0.0

    cumulative_reward = 0.0
    step_num = 0
    history_buffer = []

    for i in range(MAX_STEPS_PER_TASK):
        if done:
            break

        step_num = i + 1
        action_dict = _call_llm(task_id, obs, history_buffer)
        if action_dict is None:
            action_dict = _fallback_action(task_id, obs)

        action_json_str = json.dumps(action_dict)

        try:
            from context_router.models import CacheAction
            cache_action = CacheAction(**action_dict)
            step_resp = await env.step(cache_action)
            obs = step_resp.observation.model_dump()
            reward = float(step_resp.reward)
            done = bool(step_resp.done)
        except Exception:
            reward = 0.0
            done = True

        history_buffer.append({
            'block_id': action_dict.get('target_block_id'),
            'tactic': action_dict.get('tactic'),
            'reward': reward,
        })
        if len(history_buffer) > 3:
            history_buffer.pop(0)

        cumulative_reward += reward
        print(f"[STEP] Step: {step_num}, Action: {action_json_str}, Reward: {reward}")

    final_score = cumulative_reward / max(1, step_num)
    final_score = max(0.0, min(1.0, final_score))
    print(f"[END] Score: {final_score}")
    return final_score

async def main() -> int:
    try:
        from context_router.client import MyEnv
    except ImportError:
        import sys, os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from context_router.client import MyEnv

    all_scores = {}
    env = MyEnv(ENV_SERVER_URL)
    for task_id in TASKS:
        try:
            score = await run_task(task_id, env)
            all_scores[task_id] = score
        except Exception as e:
            print(f"[END] Score: 0.0")
            all_scores[task_id] = 0.0

    await env.close()
    print("\n--- Final Scores ---")
    for task_id, score in all_scores.items():
        print(f"  {task_id}: {score:.4f}")
    return 0

if __name__ == '__main__':
    import asyncio
    raise SystemExit(asyncio.run(main()))
