from typing import Any


VRAM_TARGET = 0.3
MAX_STEPS = 50
CRITICAL_TYPES = frozenset({"system_prompt", "code_snippet"})


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


def grader_hard(trajectory: list[Any]) -> float:
    """
    Hard task:
    - 1.0 for full survival with strong critical retention and low average VRAM.
    - Partial credit from survival, retention, VRAM control, and stability.
    """
    try:
        if not trajectory:
            return 0.0

        first = trajectory[0]
        final = trajectory[-1]
        steps = len(trajectory)

        oom_events = sum(1 for obs in trajectory if bool(_get(obs, "oom_triggered", False)))
        vram_values = [float(_get(obs, "vram_utilization", 1.0)) for obs in trajectory]
        avg_vram = sum(vram_values) / max(1, len(vram_values))

        initial_blocks = _blocks(first)
        final_blocks = _blocks(final)
        initial_critical = {
            _block_get(b, "block_type", "") for b in initial_blocks if _block_get(b, "block_type", "") in CRITICAL_TYPES
        }
        final_critical = {
            _block_get(b, "block_type", "") for b in final_blocks if _block_get(b, "block_type", "") in CRITICAL_TYPES
        }

        if initial_critical:
            retention_ratio = len(final_critical) / len(initial_critical)
        else:
            retention_ratio = 1.0

        if (
            oom_events == 0
            and steps >= MAX_STEPS
            and avg_vram < VRAM_TARGET
            and retention_ratio >= 0.8
        ):
            return 1.0

        survival_component = min(0.35, (steps / MAX_STEPS) * 0.35)
        retention_component = min(0.30, retention_ratio * 0.30)
        vram_component = max(0.0, min(0.25, (1.0 - avg_vram) * 0.25))

        if len(vram_values) > 1:
            stability = max(0.0, 1.0 - (max(vram_values) - min(vram_values)))
            stability_component = min(0.10, stability * 0.10)
        else:
            stability_component = 0.0

        oom_penalty = min(0.8, 0.30 * oom_events)

        score = (
            survival_component
            + retention_component
            + vram_component
            + stability_component
            - oom_penalty
        )
        return float(max(0.0, min(1.0, score)))

    except Exception:
        return 0.0

