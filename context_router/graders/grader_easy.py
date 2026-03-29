from typing import List

try:
    from context_router.models import CacheObservation
except ImportError:
    from models import CacheObservation

VRAM_TARGET = 0.5
MAX_STEPS = 50


def grader_easy(trajectory: List[CacheObservation]) -> float:
    """
    Evaluates the 'easy' task trajectory.
    Goal: Reduce VRAM below 50% (0.5) within 50 steps without triggering OOM.

    Scoring:
    - VRAM efficiency (60%): How well VRAM is managed relative to target
    - Survival (25%): Completing more steps is better
    - No OOM bonus (15%): Not triggering OOM is critical

    Partial credit: Available for partial VRAM improvement even if target not met.
    """
    try:
        if not trajectory:
            return 0.0

        steps = len(trajectory)

        first_obs = trajectory[0]
        final_obs = trajectory[-1]

        vram_initial = first_obs.vram_utilization
        vram_final = final_obs.vram_utilization

        oom_events = sum(1 for obs in trajectory if obs.oom_triggered)
        oom_penalty = 0.2 * oom_events

        if oom_events > 0:
            survival_score = 0.0
            vram_score = 0.0
        else:
            survival_score = min(1.0, steps / MAX_STEPS) * 0.25

            if vram_final < VRAM_TARGET:
                vram_score = (1.0 - (vram_final / VRAM_TARGET)) * 0.6
            else:
                vram_improvement = vram_initial - vram_final
                vram_score = (
                    max(0.0, vram_improvement / vram_initial * 0.3)
                    if vram_initial > 0
                    else 0.0
                )

        oom_bonus = 0.15 if oom_events == 0 else 0.0

        score = vram_score + survival_score + oom_bonus - oom_penalty

        return float(max(0.0, min(1.0, score)))

    except Exception:
        return 0.0
