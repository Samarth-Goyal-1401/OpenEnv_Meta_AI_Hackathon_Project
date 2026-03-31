from typing import Any


VRAM_TARGET = 0.4
MAX_STEPS = 50
HIGH_ATTENTION_THRESHOLD = 0.6
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


def _linear_ramp(value: float, threshold: float, scale: float) -> float:
    """Linear ramp: gives partial credit as value approaches threshold."""
    if value >= threshold:
        return scale
    return max(0.0, (value / threshold) * scale)


def _track_trajectory_retention(trajectory: list[Any]) -> float:
    """Track critical block + high-attention retention throughout trajectory."""
    if len(trajectory) < 2:
        return 0.0

    retention_over_time = []

    for obs in trajectory:
        blocks = _blocks(obs)

        has_system = any(
            _block_get(b, "block_type", "") == "system_prompt" for b in blocks
        )
        high_attention_count = sum(
            1
            for b in blocks
            if float(_block_get(b, "attention_score", 0.0)) >= HIGH_ATTENTION_THRESHOLD
        )

        score = (1.0 if has_system else 0.0) + min(1.0, high_attention_count / 2)
        retention_over_time.append(score / 2)

    avg_retention = sum(retention_over_time) / len(retention_over_time)
    return avg_retention


def _compute_vram_stability(vram_values: list[float]) -> float:
    """Compute VRAM stability score."""
    if len(vram_values) < 2:
        return 1.0

    max_vram = max(vram_values)
    min_vram = min(vram_values)
    vram_range = max_vram - min_vram

    spike_penalty = 0.0
    for i in range(1, len(vram_values)):
        change = vram_values[i] - vram_values[i - 1]
        if change > 0.10:
            spike_penalty += (change - 0.10) * 0.3

    stability = max(0.0, 1.0 - vram_range - min(0.2, spike_penalty))
    return stability


def grader_medium(trajectory: list[Any]) -> float:
    """
    Medium task:
    - 1.0 if target VRAM is met, no OOM, system prompt retained, and most
      high-attention blocks are retained throughout trajectory.
    - Partial credit combines VRAM progress, trajectory-based retention, and survival.
    """
    try:
        if not trajectory:
            return 0.0

        first = trajectory[0]
        final = trajectory[-1]

        vram_initial = float(_get(first, "vram_utilization", 1.0))
        vram_final = float(_get(final, "vram_utilization", 1.0))
        oom_events = sum(
            1 for obs in trajectory if bool(_get(obs, "oom_triggered", False))
        )
        steps = len(trajectory)

        vram_values = [float(_get(obs, "vram_utilization", 1.0)) for obs in trajectory]
        stability_score = _compute_vram_stability(vram_values)

        initial_blocks = _blocks(first)
        final_blocks = _blocks(final)

        initial_high = [
            b
            for b in initial_blocks
            if float(_block_get(b, "attention_score", 0.0)) >= HIGH_ATTENTION_THRESHOLD
        ]
        final_high = [
            b
            for b in final_blocks
            if float(_block_get(b, "attention_score", 0.0)) >= HIGH_ATTENTION_THRESHOLD
        ]

        initial_high_count = len(initial_high)
        if initial_high_count > 0:
            final_retention_ratio = min(1.0, len(final_high) / initial_high_count)
        else:
            final_retention_ratio = 1.0

        system_kept = any(
            _block_get(b, "block_type", "") == "system_prompt" for b in final_blocks
        )

        trajectory_retention = _track_trajectory_retention(trajectory)

        if (
            vram_final < VRAM_TARGET
            and oom_events == 0
            and system_kept
            and final_retention_ratio >= 0.8
        ):
            return 1.0

        vram_drop = max(0.0, vram_initial - vram_final)
        vram_component = _linear_ramp(vram_drop / max(vram_initial, 1e-6), 0.5, 0.40)
        retention_component = (0.25 if system_kept else 0.0) + (
            trajectory_retention * 0.20
        )
        survival_component = _linear_ramp(steps, MAX_STEPS, 0.15)
        target_bonus = 0.10 if vram_final < VRAM_TARGET else 0.0
        stability_component = stability_score * 0.05
        oom_penalty = min(0.6, 0.25 * oom_events)

        score = (
            vram_component
            + retention_component
            + survival_component
            + target_bonus
            + stability_component
            - oom_penalty
        )
        return float(max(0.0, min(1.0, score)))

    except Exception:
        return 0.0
