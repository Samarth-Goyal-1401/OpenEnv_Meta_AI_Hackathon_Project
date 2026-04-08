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


def _block_id(block: Any) -> int | None:
    value = _block_get(block, "block_id", None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _linear_ramp(value: float, threshold: float, scale: float) -> float:
    """Linear ramp: gives partial credit as value approaches threshold."""
    if value >= threshold:
        return scale
    return max(0.0, (value / threshold) * scale)


def _important_block_ids(blocks: list[Any]) -> set[int]:
    important_ids: set[int] = set()
    for block in blocks:
        block_id = _block_id(block)
        if block_id is None:
            continue
        block_type = _block_get(block, "block_type", "")
        attention = float(_block_get(block, "attention_score", 0.0))
        if block_type in CRITICAL_TYPES or attention >= HIGH_ATTENTION_THRESHOLD:
            important_ids.add(block_id)
    return important_ids


def _trajectory_retention(trajectory: list[Any], important_ids: set[int]) -> float:
    """Track retention of the original important block IDs throughout the episode."""
    if len(trajectory) < 2:
        return 0.0
    if not important_ids:
        return 1.0

    retention_over_time = []
    for obs in trajectory:
        current_ids = {
            block_id
            for block in _blocks(obs)
            for block_id in [_block_id(block)]
            if block_id is not None
        }
        retention_over_time.append(len(current_ids & important_ids) / len(important_ids))

    return sum(retention_over_time) / len(retention_over_time)


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

        initial_blocks = _blocks(first)
        final_blocks = _blocks(final)

        important_ids = _important_block_ids(initial_blocks)
        final_ids = {
            block_id
            for block in final_blocks
            for block_id in [_block_id(block)]
            if block_id is not None
        }
        if important_ids:
            final_retention_ratio = len(final_ids & important_ids) / len(important_ids)
        else:
            final_retention_ratio = 1.0

        system_ids = {
            block_id
            for block in initial_blocks
            if _block_get(block, "block_type", "") == "system_prompt"
            for block_id in [_block_id(block)]
            if block_id is not None
        }
        system_kept = not system_ids or bool(final_ids & system_ids)

        trajectory_retention = _trajectory_retention(trajectory, important_ids)

        if (
            vram_final < VRAM_TARGET
            and oom_events == 0
            and system_kept
            and final_retention_ratio >= 0.8
        ):
            return 0.98

        vram_drop = max(0.0, vram_initial - vram_final)
        vram_component = _linear_ramp(vram_drop / max(vram_initial, 1e-6), 0.5, 0.40)
        retention_component = (0.25 if system_kept else 0.0) + (
            ((trajectory_retention + final_retention_ratio) / 2.0) * 0.20
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
        return float(max(0.01, min(0.98, score)))

    except Exception:
        return 0.01
