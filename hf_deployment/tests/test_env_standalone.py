"""
Dev 1 standalone checks for ContextRouterEnv.

Run from `context_router/`:
    python tests/test_env_standalone.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from context_router.models import CacheAction, EvictionTactic
from context_router.server.context_env import ContextRouterEnv


def _snapshot_blocks(blocks):
    return [block.model_dump() for block in blocks]


def main() -> None:
    env = ContextRouterEnv()

    # Test 1: reset() determinism for seeded episodes.
    obs1 = env.reset(seed=42)
    obs2 = env.reset(seed=42)
    assert obs1.vram_utilization == obs2.vram_utilization, "FAIL: not deterministic"
    assert obs1.incoming_tokens == obs2.incoming_tokens, "FAIL: incoming tokens not deterministic"
    assert _snapshot_blocks(obs1.memory_blocks) == _snapshot_blocks(obs2.memory_blocks), "FAIL: blocks not deterministic"
    assert obs1.done is False, "FAIL: done should be False on reset"

    # Test 2: step() handles invalid block id without crashing.
    bad = CacheAction(target_block_id=-999, tactic=EvictionTactic.EVICT)
    invalid_obs = env.step(bad)
    assert isinstance(invalid_obs.reward, float), "FAIL: reward not float"
    assert isinstance(invalid_obs.done, bool), "FAIL: done not bool"

    # Test 3: max steps are enforced.
    env.reset(seed=1)
    stop_step = None
    for step_num in range(1, 61):
        step_obs = env.step(CacheAction(target_block_id=0, tactic=EvictionTactic.RETAIN))
        if step_obs.done:
            stop_step = step_num
            break
    assert stop_step is not None, "FAIL: episode never terminated"
    assert stop_step <= env.MAX_STEPS, f"FAIL: exceeded MAX_STEPS (stopped at {stop_step})"

    # Test 4: episode_id changes between resets.
    env.reset(seed=7)
    first_episode_id = env.state.episode_id
    env.reset(seed=8)
    second_episode_id = env.state.episode_id
    assert first_episode_id != second_episode_id, "FAIL: episode_id did not change across resets"

    print("All Dev 1 standalone tests passed")


if __name__ == "__main__":
    main()
