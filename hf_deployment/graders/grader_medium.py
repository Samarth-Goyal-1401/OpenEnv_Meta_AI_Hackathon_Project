from typing import Any


VRAM_TARGET = 0.4
MAX_STEPS = 50
HIGH_ATTENTION_THRESHOLD = 0.6


def _get(obs: Any, key: str, default: Any) -> Any:
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def _blocks(obs: Any) -> list[Any]:
    value = _get(obs, "memory_blocks", [])
    if isinstance(value, list):
        return value
    return []


def _block_get(block: Any, key: str, default: Any) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def grader_medium(trajectory: list[Any]) -> float:
    """
    Medium task:
    - 1.0 if target VRAM is met, no OOM, system prompt retained, and most
      high-attention blocks are retained.
    - Partial credit combines VRAM progress, retention, and survival.
    """
    try:
        if not trajectory:
            return 0.0

        first = trajectory[0]
        final = trajectory[-1]

        vram_initial = float(_get(first, "vram_utilization", 1.0))
        vram_final = float(_get(final, "vram_utilization", 1.0))
        oom_events = sum(1 for obs in trajectory if bool(_get(obs, "oom_triggered", False)))
        steps = len(trajectory)

        initial_blocks = _blocks(first)
        final_blocks = _blocks(final)

        initial_high = [
            b for b in initial_blocks if float(_block_get(b, "attention_score", 0.0)) >= HIGH_ATTENTION_THRESHOLD
        ]
        final_high = [
            b for b in final_blocks if float(_block_get(b, "attention_score", 0.0)) >= HIGH_ATTENTION_THRESHOLD
        ]

        initial_high_count = len(initial_high)
        if initial_high_count > 0:
            retention_ratio = min(1.0, len(final_high) / initial_high_count)
        else:
            retention_ratio = 1.0

        system_kept = any(_block_get(b, "block_type", "") == "system_prompt" for b in final_blocks)

        if (
            vram_final < VRAM_TARGET
            and oom_events == 0
            and system_kept
            and retention_ratio >= 0.8
        ):
            return 1.0

        vram_drop = max(0.0, vram_initial - vram_final)
        vram_component = min(0.40, vram_drop / max(vram_initial, 1e-6) * 0.40)
        retention_component = (0.25 if system_kept else 0.0) + (retention_ratio * 0.20)
        survival_component = min(0.15, (steps / MAX_STEPS) * 0.15)
        target_bonus = 0.10 if vram_final < VRAM_TARGET else 0.0
        oom_penalty = min(0.6, 0.25 * oom_events)

        score = vram_component + retention_component + survival_component + target_bonus - oom_penalty
        return float(max(0.0, min(1.0, score)))

    except Exception:
        return 0.0

