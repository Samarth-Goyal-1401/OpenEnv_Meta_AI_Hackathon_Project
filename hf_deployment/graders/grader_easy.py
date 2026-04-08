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
        oom_events = sum(1 for obs in trajectory if bool(_get(obs, "oom_triggered", False)))
        steps = len(trajectory)

        if vram_final < VRAM_TARGET and oom_events == 0:
            return 0.99

        vram_drop = max(0.0, vram_initial - vram_final)
        baseline = min(0.45, vram_drop / max(vram_initial, 1e-6) * 0.45)
        survival = min(0.35, (steps / MAX_STEPS) * 0.35)
        below_target_bonus = 0.20 if vram_final < VRAM_TARGET else 0.0
        oom_penalty = min(0.6, 0.2 * oom_events)

        score = baseline + survival + below_target_bonus - oom_penalty
        return float(max(0.01, min(0.99, score)))

    except Exception:
        return 0.01

