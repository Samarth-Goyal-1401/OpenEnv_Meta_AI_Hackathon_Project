# Edge GPU Context Router (OpenEnv Hackathon)

An OpenEnv-compatible environment for KV-cache/VRAM management during local LLM inference.
Agents choose when to `evict`, `retain`, or `compress` memory blocks to avoid OOM while preserving critical context.

## Highlights

- Deterministic multi-step control task (easy/medium/hard)
- OpenEnv API compatible (`/reset`, `/step`, `/state`, `/schema`, `/metadata`, `/health`)
- Built-in trajectory graders with partial credit
- Baseline runner + test suite for reproducible validation

## Task Model

Each step, the agent outputs:

- `target_block_id`
- `tactic` = `evict | retain | compress`
- `priority` (hard mode only)

Observation includes:

- `vram_utilization` in `[0.0, 1.0]`
- `incoming_tokens`
- `memory_blocks` (`block_id`, `block_type`, `attention_score`, `token_count`, `age`)
- `oom_triggered`, `message`, `done`, `reward`

### Delayed Hallucination Penalty

If critical hidden context is evicted, a delayed `HALLUCINATION_ERROR` spike can be injected after 5 steps.
This discourages greedy short-horizon strategies.

## Difficulty Tiers

- **Easy**: reduce VRAM below `0.5` without OOM
- **Medium**: reduce below `0.4` while retaining important blocks
- **Hard**: long-horizon stability + retention + priority control

## Local Quickstart (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .\context_router
uvicorn context_router.server.app:app --host 0.0.0.0 --port 8000
```

## Validate Locally

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/tasks
curl -X POST http://localhost:8000/baseline
.\.venv\Scripts\python.exe -m pytest context_router\tests -q
```

Optional OpenEnv validation:

```powershell
cd context_router
openenv validate --url http://localhost:8000
```

## Grading Notes

Current graders are bounded to keep scores safely below 1.00 formatting edge cases.
The scoring interval is clamped to `[0.01, 0.98]`.

Main grader files:

- `context_router/graders/grader_easy.py`
- `context_router/graders/grader_medium.py`
- `context_router/graders/grader_hard.py`

## Repository Layout

- `context_router/` - primary environment implementation
- `hf_deployment/` - deployment mirror for Hugging Face Space
- `tests/` - additional repository-level checks
- `inference.py` - root inference entrypoint
- `push_to_hf.py` - HF Space deployment helper

## Deployment

GitHub remote is configured for this repo.
Hugging Face Space deployment is handled from root via:

```powershell
.\.venv\Scripts\python.exe .\push_to_hf.py --wait --no-proxy
```
