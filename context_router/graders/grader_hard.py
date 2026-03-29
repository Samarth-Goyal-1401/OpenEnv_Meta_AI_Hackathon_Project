from typing import List

try:
    from context_router.models import CacheObservation
except ImportError:
    from models import CacheObservation

VRAM_TARGET = 0.3
MAX_STEPS = 50
CRITICAL_BLOCK_TYPES = frozenset({"system_prompt", "code_snippet"})


def grader_hard(trajectory: List[CacheObservation]) -> float:
    """
    Evaluates the 'hard' task trajectory.
    Goal: Optimize VRAM under high token pressure and RAG spikes.

    Scoring:
    - Survival (35%): Primary goal - just surviving is hard
    - Critical block retention (30%): Keep system_prompt and code_snippet
    - VRAM efficiency (25%): Keep VRAM low on average
    - Stability (10%): Consistent VRAM management

    Partial credit: Available for partial survival and partial improvements.
    """
    try:
        if not trajectory:
            return 0.0

        steps = len(trajectory)

        first_obs = trajectory[0]
        final_obs = trajectory[-1]

        oom_events = sum(1 for obs in trajectory if obs.oom_triggered)
        oom_penalty = 0.3 * oom_events

        if oom_events > 0:
            survival_score = 0.0
            vram_score = 0.0
            retention_score = 0.0
            stability_score = 0.0
        else:
            survival_score = (steps / MAX_STEPS) * 0.35

            avg_vram = sum(obs.vram_utilization for obs in trajectory) / steps
            if avg_vram < VRAM_TARGET:
                vram_score = (1.0 - (avg_vram / VRAM_TARGET)) * 0.25
            else:
                vram_score = max(0.0, (1.0 - avg_vram) * 0.15)

            first_types = {b.block_type for b in first_obs.memory_blocks}
            final_types = {b.block_type for b in final_obs.memory_blocks}

            critical_initial = first_types & CRITICAL_BLOCK_TYPES
            critical_final = final_types & CRITICAL_BLOCK_TYPES

            if len(critical_initial) > 0:
                retention_ratio = len(critical_final) / len(critical_initial)
            else:
                retention_ratio = 1.0 if len(critical_final) > 0 else 0.0

            retention_score = retention_ratio * 0.30

            vram_values = [obs.vram_utilization for obs in trajectory]
            if len(vram_values) > 1:
                max_vram = max(vram_values)
                min_vram = min(vram_values)
                stability = 1.0 - (max_vram - min_vram)
                stability_score = stability * 0.10
            else:
                stability_score = 0.10

        score = (
            survival_score
            + retention_score
            + vram_score
            + stability_score
            - oom_penalty
        )

        return float(max(0.0, min(1.0, score)))

    except Exception:
        return 0.0
