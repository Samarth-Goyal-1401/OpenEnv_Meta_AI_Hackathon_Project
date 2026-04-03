#!/usr/bin/env python3
"""
Verify all 4 hackathon upgrades are working correctly.

Tests:
  Task 1: inference.py imports and has [START]/[STEP]/[END] logging
  Task 2: Dashboard served at / with /dashboard/state endpoint
  Task 3: Delayed penalties fire 5 steps after critical block eviction
  Task 4: Invalid block_id returns done=True with Fatal error message
"""

import asyncio
import json
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx

BASE_URL = "http://localhost:8000"
RESULTS = []


def log(ok: bool, test: str, detail: str = ""):
    status = "✅ PASS" if ok else "❌ FAIL"
    RESULTS.append((ok, test))
    print(f"  {status}: {test}")
    if detail:
        print(f"         {detail}")


async def wait_for_server(retries=10, delay=1):
    for _ in range(retries):
        try:
            async with httpx.AsyncClient(timeout=5, trust_env=False) as c:
                r = await c.get(f"{BASE_URL}/tasks")
                if r.status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(delay)
    return False


async def test_task2_dashboard():
    """Task 2: Dashboard served at /"""
    print("\n── Task 2: Visual Dashboard ──")
    async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
        # Test GET /
        r = await c.get(f"{BASE_URL}/")
        log(r.status_code == 200, "GET / returns 200")
        log("Edge GPU Context Router" in r.text, "HTML contains project title")
        log("vram-bar" in r.text, "HTML contains VRAM bar component")
        log("blocksGrid" in r.text, "HTML contains blocks grid component")

        # Test GET /dashboard/state
        r = await c.get(f"{BASE_URL}/dashboard/state")
        log(r.status_code == 200, "GET /dashboard/state returns 200")
        data = r.json()
        log("vram_utilization" in data, "/dashboard/state has vram_utilization")
        log("memory_blocks" in data, "/dashboard/state has memory_blocks")


async def test_task3_delayed_penalties():
    """Task 3: Delayed penalties fire 5 steps after critical block eviction."""
    print("\n── Task 3: Delayed Penalties ──")
    try:
        from context_router.client import MyEnv
        from context_router.models import CacheAction, EvictionTactic
    except ImportError:
        import sys, os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from context_router.client import MyEnv
        from context_router.models import CacheAction, EvictionTactic

    env = MyEnv(BASE_URL)
    step_result = await env.reset()
    obs = step_result.observation
    blocks = obs.memory_blocks

    log(len(blocks) > 0, f"Reset returns {len(blocks)} blocks")

    # Find a system_prompt block to evict (may be critical)
    system_blocks = [b for b in blocks if b.block_type == "system_prompt"]
    if not system_blocks:
        log(False, "No system_prompt block found to test")
        await env.close()
        return

    target_bid = system_blocks[0].block_id
    log(True, f"Found system_prompt block #{target_bid} to evict")

    # Evict the system_prompt block
    action = CacheAction(target_block_id=target_bid, tactic=EvictionTactic.EVICT)
    step_result = await env.step(action)
    obs1 = step_result.observation
    msg1 = obs1.message
    log("Evicted" in msg1 or "evict" in msg1.lower(), f"Eviction message received", msg1[:100])

    # Run 6 more steps to see if hallucination event fires
    hallucination_found = False
    for i in range(7):
        current_blocks = obs1.memory_blocks
        if not current_blocks:
            break
        bid = current_blocks[0].block_id
        action = CacheAction(target_block_id=bid, tactic=EvictionTactic.RETAIN)
        step_result = await env.step(action)
        obs1 = step_result.observation
        msg = obs1.message
        if "HALLUCINATION" in msg:
            hallucination_found = True
            log(True, f"Hallucination event fired at step {i+2}", msg[:120])
            break

    if not hallucination_found:
        log(False, "Hallucination event did NOT fire (block may not have been critical)")
        print("         Note: This is expected ~50% of the time since critical blocks are random")
    
    await env.close()

async def test_task4_hardening():
    """Task 4: Invalid block_id returns done=True."""
    print("\n── Task 4: Server Hardening ──")
    try:
        from context_router.client import MyEnv
        from context_router.models import CacheAction, EvictionTactic
    except ImportError:
        from context_router.client import MyEnv
        from context_router.models import CacheAction, EvictionTactic

    env = MyEnv(BASE_URL)
    await env.reset()

    # Send invalid block_id
    action = CacheAction(target_block_id=99999, tactic=EvictionTactic.EVICT)
    step_result = await env.step(action)
    done = step_result.done
    message = step_result.observation.message

    log(done is True, f"done=True on invalid block_id", f"done={done}")
    log("Fatal error" in message, f"Message contains 'Fatal error'", message)
    await env.close()
    
    # Send malformed JSON (keep using httpx for this HTTP-level test)
    async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
        r = await c.post(f"{BASE_URL}/step", content=b"not-json", headers={"Content-Type": "application/json"})
        log(r.status_code != 500, f"Malformed JSON returns {r.status_code} (not 500)")


async def test_task1_inference_imports():
    """Task 1: Verify inference.py has correct structure."""
    print("\n── Task 1: Inference Script Structure ──")
    inference_path = os.path.join(os.path.dirname(__file__), "..", "inference.py")
    with open(inference_path, "r") as f:
        content = f.read()

    log("from openai import OpenAI" in content, "Uses openai.OpenAI client")
    log("API_BASE_URL" in content, "Reads API_BASE_URL env var")
    log("MODEL_NAME" in content, "Reads MODEL_NAME env var")
    log("HF_TOKEN" in content, "Reads HF_TOKEN env var")
    log('[START] Task:' in content, "Emits [START] log format")
    log('[STEP] Step:' in content, "Emits [STEP] log format")
    log('[END] Score:' in content, "Emits [END] log format")
    log("_fallback_action" in content, "Has fallback action on LLM failure")


async def main():
    print("=" * 60)
    print("  Edge GPU Context Router — Upgrade Verification Suite")
    print("=" * 60)

    # Test Task 1 (static analysis — no server needed)
    await test_task1_inference_imports()

    # Wait for server
    print("\n⏳ Waiting for server at", BASE_URL, "...")
    server_ready = await wait_for_server()
    if not server_ready:
        print("❌ Server not reachable! Start it with: uvicorn context_router.server.app:app --port 8000")
        sys.exit(1)
    print("✅ Server is ready!\n")

    # Test Task 2, 3, 4
    await test_task2_dashboard()
    await test_task4_hardening()
    await test_task3_delayed_penalties()

    # Summary
    passed = sum(1 for ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total} tests passed")
    print(f"{'=' * 60}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
