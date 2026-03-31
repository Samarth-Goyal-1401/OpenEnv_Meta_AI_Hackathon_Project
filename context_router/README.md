---
title: Context Router Environment
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
---

# Edge GPU Context Router - OpenEnv Environment

## Overview
Edge GPU Context Router simulates memory management for local LLM inference under VRAM pressure.
The agent decides which memory block to `evict`, `retain`, or `compress` to keep usage stable
while preserving critical context (`system_prompt`, `code_snippet`).

Note on units: the environment models VRAM pressure using token-capacity as a proxy for KV-cache
memory usage. `vram_utilization` is reported as a fraction in `[0.0, 1.0]` of the current token
load divided by the task's configured capacity, not literal GPU GB.

## Action Space
| Field | Type | Valid Values | Description |
|---|---|---|---|
| `target_block_id` | `int` | `>= 0` | Block identifier selected for this step. |
| `tactic` | `EvictionTactic` | `evict`, `retain`, `compress` | Operation applied to the chosen block. |
| `priority` | `int \| None` | `1..5` or omitted | Optional hard-task signal (`1` lowest importance, `5` highest). |

Task-specific schemas:
- Easy: `target_block_id`, `tactic` in `evict|retain`
- Medium: `target_block_id`, `tactic` in `evict|retain|compress`
- Hard: `target_block_id`, `tactic` in `evict|retain|compress`, and `priority` in `1..5`

## Observation Space
| Field | Type | Description |
|---|---|---|
| `vram_utilization` | `float` | Current VRAM usage ratio in `[0.0, 1.0]`. |
| `incoming_tokens` | `int` | New token load at the current step. |
| `memory_blocks` | `List[MemoryBlockInfo]` | Snapshot of block metadata (`block_id`, `block_type`, `attention_score`, `token_count`, `age`). |
| `oom_triggered` | `bool` | True when capacity overflow occurs. |
| `message` | `str` | Human-readable status for the step. |
| `done` | `bool` | Episode completion flag (inherited from OpenEnv `Observation`). |
| `reward` | `float` | Step reward value (inherited from OpenEnv `Observation`). |

## Tasks
| Task | Difficulty | Description | Success Condition |
|---|---|---|---|
| `easy` | easy | Lower VRAM below 50% with a simple tactic set. | Final `vram_utilization < 0.5` and no OOM. |
| `medium` | medium | Balance VRAM reduction with context retention. | Final `vram_utilization < 0.4`, no OOM, retain `system_prompt` and most high-attention blocks. |
| `hard` | hard | Survive high-pressure workloads with stability and retention. | Reach 50 steps with no OOM, low average VRAM, and strong critical-block retention. |

## Reward Function
Final episode grading is done by task-specific graders.

Easy grader:
```text
if final_vram < 0.5 and oom_events == 0: score = 1.0
else:
  vram_drop = max(0, vram_initial - vram_final)
  baseline = min(0.45, (vram_drop / max(vram_initial, 1e-6)) * 0.45)
  survival = min(0.35, (steps / 50) * 0.35)
  below_target_bonus = 0.20 if final_vram < 0.5 else 0.0
  oom_penalty = min(0.6, 0.2 * oom_events)
  score = clamp(baseline + survival + below_target_bonus - oom_penalty)
```

Medium grader:
```text
if final_vram < 0.4 and oom_events == 0 and system_kept and retention_ratio >= 0.8:
  score = 1.0
else:
  vram_component = min(0.40, (vram_drop / max(vram_initial, 1e-6)) * 0.40)
  retention_component = (0.25 if system_kept else 0.0) + (retention_ratio * 0.20)
  survival_component = min(0.15, (steps / 50) * 0.15)
  target_bonus = 0.10 if final_vram < 0.4 else 0.0
  oom_penalty = min(0.6, 0.25 * oom_events)
  score = clamp(vram_component + retention_component + survival_component + target_bonus - oom_penalty)
```

Hard grader:
```text
if oom_events == 0 and steps >= 50 and avg_vram < 0.3 and retention_ratio >= 0.8:
  score = 1.0
else:
  survival_component = min(0.35, (steps / 50) * 0.35)
  retention_component = min(0.30, retention_ratio * 0.30)
  vram_component = min(0.25, max(0.0, (1.0 - avg_vram) * 0.25))
  stability_component = min(0.10, max(0.0, 1.0 - (max_vram - min_vram)) * 0.10)
  oom_penalty = min(0.8, 0.30 * oom_events)
  score = clamp(survival_component + retention_component + vram_component + stability_component - oom_penalty)
```

Hard priority mechanism in the environment:
```text
expected_priority = heuristic(block_type, attention, age, token_count) in [1..5]
if hard and priority is missing or far from expected:
  inject extra priority_spill tokens (80 or 160)
```

## Setup Instructions
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn context_router.server.app:app --host 0.0.0.0 --port 8000
set CONTEXT_ROUTER_BASE_URL=<BASE_URL>
```

## Example Episode
```python
import asyncio
import os

from context_router.client import MyEnv
from context_router.models import CacheAction, EvictionTactic


async def run_episode() -> None:
    base_url = os.environ["CONTEXT_ROUTER_BASE_URL"]
    env = MyEnv(base_url)
    reset_result = await env.reset(seed=42)
    obs = reset_result.observation

    for _ in range(10):
        blocks = obs.memory_blocks
        target_block_id = blocks[0].block_id if blocks else 0
        action = CacheAction(target_block_id=target_block_id, tactic=EvictionTactic.EVICT)
        step_result = await env.step(action)
        obs = step_result.observation
        if step_result.done:
            break

    print("Final VRAM:", obs.vram_utilization)


if __name__ == "__main__":
    asyncio.run(run_episode())
```

## Validation Checklist
Run these commands from `meta_hackathon` to verify packaging, tests, and OpenEnv contract:

```bash
.\.venv\Scripts\python.exe -m pytest context_router\tests -q
.\.venv\Scripts\python.exe context_router\baseline\run_baseline.py --base-url http://localhost:8000
cd context_router
openenv validate --url http://localhost:8000
```

Expected outputs (March 31, 2026 run):

```text
pytest: 38 passed
baseline: easy=1.0000 medium=0.3657 hard=0.3721
openenv validate: passed=true (6/6 required checks)
```

## API Endpoints
- `GET /health`
- `GET /tasks`
- `POST /reset`
- `POST /step`
- `GET /state`
- `POST /grader`
- `POST /baseline`
- `GET /schema`
- `GET /metadata`
