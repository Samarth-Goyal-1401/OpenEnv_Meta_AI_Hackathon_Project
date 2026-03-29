# Edge GPU Context Router — OpenEnv Environment

## 1. Overview
The **Edge GPU Context Router** simulates a KV-cache management system for local LLM inference on consumer-grade hardware. The RL agent acts as a context router, deciding which attention blocks to keep in VRAM, which to compress, and which to evict to prevent Out-of-Memory (OOM) crashes while maintaining generative quality.

## 2. Action Space
The agent emits a `CacheAction` with the following schema:

| Field | Type | Description |
|-------|------|-------------|
| `target_block_id` | `int` | Unique ID of the memory block to manipulate. |
| `tactic` | `EvictionTactic` | Operation: `RETAIN` (0), `EVICT` (1), `COMPRESS` (2). |

## 3. Observation Space
The environment returns a `CacheObservation` at each step:

| Field | Type | Description |
|-------|------|-------------|
| `vram_utilization` | `float` | Current VRAM usage (0.0 to 1.0). |
| `incoming_tokens` | `int` | Number of tokens in the current request. |
| `memory_blocks` | `List` | List of `MemoryBlockInfo` (id, type, attention, etc.). |
| `oom_triggered` | `bool` | True if the memory limit was exceeded. |
| `message` | `str` | Status update or error data. |

## 4. Tasks
| Task | Difficulty | Pressure | Description |
|------|------------|----------|-------------|
| **Easy** | 0.1 | Low | Maintain VRAM < 0.5 under uniform load. |
| **Medium** | 0.5 | Medium | Power-law access; must keep high-attention blocks. |
| **Hard** | 0.9 | High | RAG spikes; requires aggressive compression/eviction. |

## 5. Reward Function
Graders provide a final float score `[0.0, 1.0]` based on:
- **VRAM Efficiency (Variable %)**: Target thresholds (0.5 for Easy, 0.4 for Medium, 0.3 for Hard).
- **Attention/Block Retention**: Tracks `system_prompt` and high-attention blocks.
- **Survival (Variable %)**: Rewards completing the full episode (50 steps).
- **OOM Penalties**: Direct reduction for Out-of-Memory events.

**Easy Goal**: Manage `vram_utilization` < 0.5 without OOM.
**Medium Goal**: Manage `vram_utilization` < 0.4 while retaining high-attention context.
**Hard Goal**: Manage `vram_utilization` < 0.3 under high token/RAG pressure.

## 6. Setup & Execution
This environment is built using `openenv-core`.

```bash
# 1. Start the server
python -m context_router.server.app

# 2. Run the baseline evaluation
python context_router/baseline/run_baseline.py --base-url http://localhost:8000
```

### Example Usage (Python Client)
```python
from context_router.client import MyEnv
from context_router.models import CacheAction, EvictionTactic
import asyncio

async def main():
    env = MyEnv("http://localhost:8000")
    obs = await env.reset(seed=42)
    
    # Naive policy: Evict first block
    action = CacheAction(target_block_id=0, tactic=EvictionTactic.EVICT)
    res = await env.step(action)
    print(f"VRAM: {res.observation.vram_utilization}")

asyncio.run(main())
```

---
**Submission Metadata**
- **Framework:** OpenEnv v1.x
- **Language:** Python 3.12+
- **Deterministic:** Yes (via Seed)
