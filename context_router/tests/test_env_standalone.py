"""
Dev 1 standalone checks for ContextRouterEnv.

Run from `context_router/`:
    python tests/test_env_standalone.py
"""

from context_router.models import CacheAction, EvictionTactic
from context_router.server.context_env import ContextRouterEnv


def _snapshot_blocks(blocks):
    return [block.model_dump() for block in blocks]


def test_reset_seed_is_deterministic() -> None:
    env = ContextRouterEnv()
    obs1 = env.reset(seed=42)
    obs2 = env.reset(seed=42)
    assert obs1.vram_utilization == obs2.vram_utilization
    assert obs1.incoming_tokens == obs2.incoming_tokens
    assert _snapshot_blocks(obs1.memory_blocks) == _snapshot_blocks(obs2.memory_blocks)
    assert obs1.done is False


def test_step_with_invalid_block_id_does_not_crash() -> None:
    env = ContextRouterEnv()
    env.reset(seed=42)
    bad = CacheAction(target_block_id=-999, tactic=EvictionTactic.EVICT)
    invalid_obs = env.step(bad)
    assert isinstance(invalid_obs.reward, float)
    assert isinstance(invalid_obs.done, bool)


def test_max_steps_are_enforced() -> None:
    env = ContextRouterEnv()
    env.reset(seed=1)
    stop_step = None
    for step_num in range(1, 61):
        step_obs = env.step(CacheAction(target_block_id=0, tactic=EvictionTactic.RETAIN))
        if step_obs.done:
            stop_step = step_num
            break
    assert stop_step is not None
    assert stop_step <= env.MAX_STEPS


def test_episode_id_changes_between_resets() -> None:
    env = ContextRouterEnv()
    env.reset(seed=7)
    first_episode_id = env.state.episode_id
    env.reset(seed=8)
    second_episode_id = env.state.episode_id
    assert first_episode_id != second_episode_id


def main() -> None:
    test_reset_seed_is_deterministic()
    test_step_with_invalid_block_id_does_not_crash()
    test_max_steps_are_enforced()
    test_episode_id_changes_between_resets()
    print("All Dev 1 standalone tests passed")


if __name__ == "__main__":
    main()
