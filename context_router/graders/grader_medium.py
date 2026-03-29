from typing import List

try:
    from context_router.models import CacheObservation
except ImportError:
    from models import CacheObservation

VRAM_TARGET = 0.4
MAX_STEPS = 50
HIGH_ATTENTION_THRESHOLD = 0.6


def grader_medium(trajectory: List[CacheObservation]) -> float:
    """
    Evaluates the 'medium' task trajectory.
    Goal: Reduce VRAM below 40% (0.4) while keeping high-attention blocks.

    Scoring:
    - VRAM efficiency (45%): Target < 0.4 with partial credit for improvement
    - Attention retention (35%): Keep system_prompt and high-attention blocks
    - Survival (20%): Complete more steps

    Partial credit: Available for partial VRAM reduction and partial attention retention.
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
        oom_penalty = 0.25 * oom_events

        if oom_events > 0:
            survival_score = 0.0
            vram_score = 0.0
            attention_score = 0.0
        else:
            survival_score = min(1.0, steps / MAX_STEPS) * 0.20

            if vram_final < VRAM_TARGET:
                vram_score = (1.0 - (vram_final / VRAM_TARGET)) * 0.45
            else:
                vram_improvement = vram_initial - vram_final
                vram_score = (
                    max(0.0, vram_improvement / vram_initial * 0.25)
                    if vram_initial > 0
                    else 0.0
                )

            system_kept = any(
                b.block_type == "system_prompt" for b in final_obs.memory_blocks
            )

            high_attn_blocks = [
                b
                for b in final_obs.memory_blocks
                if b.attention_score >= HIGH_ATTENTION_THRESHOLD
            ]
            high_attn_count = len(high_attn_blocks)

            initial_high_attn = [
                b
                for b in first_obs.memory_blocks
                if b.attention_score >= HIGH_ATTENTION_THRESHOLD
            ]
            initial_high_attn_count = len(initial_high_attn)

            if initial_high_attn_count > 0:
                attn_retention_ratio = min(
                    1.0, high_attn_count / initial_high_attn_count
                )
            else:
                attn_retention_ratio = 1.0 if high_attn_count > 0 else 0.0

            attention_score = (0.5 if system_kept else 0.0) + (
                attn_retention_ratio * 0.5
            )
            attention_score = attention_score * 0.35

        score = vram_score + attention_score + survival_score - oom_penalty

        return float(max(0.0, min(1.0, score)))

    except Exception:
        return 0.0
