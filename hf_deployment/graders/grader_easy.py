from typing import Any


VRAM_TARGET = 0.5
MAX_STEPS = 50


def _get(obs: Any, key: str, default: Any) -> Any:
    if isinstance(obs, dict):
        return obs.get(key, default)
    return getattr(obs, key, default)


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

        baseline = 0.01

        vram_drop = max(0.0, vram_initial - vram_final)
        vram_component = min(0.40, (vram_drop / max(vram_initial, 1e-6)) * 0.40)
        survival = min(0.35, (steps / MAX_STEPS) * 0.35)
        below_target_bonus = 0.22 if vram_final < VRAM_TARGET else 0.0
        oom_penalty = min(0.6, 0.25 * oom_events)

        raw_score = baseline + vram_component + survival + below_target_bonus - oom_penalty
        return float(max(0.01, min(0.98, raw_score)))

    except Exception:
        return 0.01
