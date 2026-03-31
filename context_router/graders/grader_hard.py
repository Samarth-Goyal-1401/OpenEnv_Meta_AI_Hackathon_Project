from typing import Any


VRAM_TARGET = 0.3
MAX_STEPS = 50
CRITICAL_TYPES = frozenset({"system_prompt", "code_snippet"})
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


def _linear_ramp(value: float, threshold: float, scale: float) -> float:
    """Linear ramp: gives partial credit as value approaches threshold."""
    if value >= threshold:
        return scale
    return max(0.0, (value / threshold) * scale)


def _track_trajectory_retention(trajectory: list[Any]) -> float:
    """Track critical block retention throughout entire trajectory, not just at end."""
    if len(trajectory) < 2:
        return 0.0

    critical_retention_over_time = []

    for obs in trajectory:
        blocks = _blocks(obs)
        current_critical = {
            _block_get(b, "block_type", "")
            for b in blocks
            if _block_get(b, "block_type", "") in CRITICAL_TYPES
        }
        critical_retention_over_time.append(len(current_critical))

    initial_count = critical_retention_over_time[0]
    if initial_count == 0:
        return 1.0

    avg_retention = sum(critical_retention_over_time) / len(
        critical_retention_over_time
    )
    return avg_retention / initial_count


def _compute_vram_stability(vram_values: list[float]) -> float:
    """Compute VRAM stability score based on variance and spikes."""
    if len(vram_values) < 2:
        return 1.0

    max_vram = max(vram_values)
    min_vram = min(vram_values)
    vram_range = max_vram - min_vram

    spike_penalty = 0.0
    for i in range(1, len(vram_values)):
        change = vram_values[i] - vram_values[i - 1]
        if change > 0.15:
            spike_penalty += (change - 0.15) * 0.5

    stability = max(0.0, 1.0 - vram_range - min(0.3, spike_penalty))
    return stability


def grader_hard(trajectory: list[Any]) -> float:
    """
    Hard task:
    - 1.0 for full survival with strong critical retention and low average VRAM.
    - Partial credit from survival, trajectory-based retention, VRAM control, and stability.
    """
    try:
        if not trajectory:
            return 0.0

        first = trajectory[0]
        final = trajectory[-1]
        steps = len(trajectory)

        oom_events = sum(
            1 for obs in trajectory if bool(_get(obs, "oom_triggered", False))
        )
        vram_values = [float(_get(obs, "vram_utilization", 1.0)) for obs in trajectory]
        avg_vram = sum(vram_values) / max(1, len(vram_values))

        initial_blocks = _blocks(first)
        final_blocks = _blocks(final)
        initial_critical = {
            _block_get(b, "block_type", "")
            for b in initial_blocks
            if _block_get(b, "block_type", "") in CRITICAL_TYPES
        }
        final_critical = {
            _block_get(b, "block_type", "")
            for b in final_blocks
            if _block_get(b, "block_type", "") in CRITICAL_TYPES
        }

        if initial_critical:
            final_retention_ratio = len(final_critical) / len(initial_critical)
        else:
            final_retention_ratio = 1.0

        trajectory_retention = _track_trajectory_retention(trajectory)
        stability_score = _compute_vram_stability(vram_values)

        if (
            oom_events == 0
            and steps >= MAX_STEPS
            and avg_vram < VRAM_TARGET
            and final_retention_ratio >= 0.8
            and trajectory_retention >= 0.8
        ):
            return 1.0

        survival_component = _linear_ramp(steps, MAX_STEPS, 0.35)
        retention_component = _linear_ramp(trajectory_retention, 0.8, 0.30)
        vram_component = _linear_ramp(1.0 - avg_vram, 1.0 - VRAM_TARGET, 0.25)
        stability_component = stability_score * 0.10

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
