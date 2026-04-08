from typing import Any


VRAM_TARGET = 0.5
MAX_STEPS = 50


def _get(obs: Any, key: str, default: Any) -> Any:
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


def _linear_ramp(value: float, threshold: float, scale: float) -> float:
    """Linear ramp: gives partial credit as value approaches threshold."""
    if value >= threshold:
        return scale
    return max(0.0, (value / threshold) * scale)


def _compute_vram_stability(vram_values: list[float]) -> float:
    """Compute VRAM stability score - reward consistent VRAM reduction."""
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


def grader_easy(trajectory: list[Any]) -> float:
    """
    Easy task:
    - 1.0 if final VRAM < 0.5 with no OOM events.
    - Partial credit for VRAM improvement and surviving more steps.
    """
    try:
        if not trajectory:
            return 0.01

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

        if vram_final < VRAM_TARGET and oom_events == 0:
            return 0.99

        vram_drop = max(0.0, vram_initial - vram_final)
        vram_component = _linear_ramp(vram_drop / max(vram_initial, 1e-6), 0.5, 0.45)
        survival_component = _linear_ramp(steps, MAX_STEPS, 0.35)
        below_target_bonus = 0.20 if vram_final < VRAM_TARGET else 0.0
        stability_component = stability_score * 0.10
        oom_penalty = min(0.6, 0.2 * oom_events)

        score = (
            vram_component
            + survival_component
            + below_target_bonus
            + stability_component
            - oom_penalty
        )
        return float(max(0.01, min(0.99, score)))

    except Exception:
        return 0.01
