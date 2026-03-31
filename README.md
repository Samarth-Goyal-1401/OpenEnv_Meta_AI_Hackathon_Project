# Edge GPU Context Router (OpenEnv Hackathon)

An OpenEnv-compatible RL environment that simulates KV-cache / VRAM pressure during local LLM inference. The agent must decide what context to **evict**, **retain**, or **compress** to avoid OOM while preserving critical information like the `system_prompt` and `code_snippet`.

This repo was built for the Meta x OpenEnv hackathon. The actual environment lives in `context_router/`.

## What The Agent Controls

At each step the agent selects:

- `target_block_id`: which memory block to operate on
- `tactic`: `evict` | `retain` | `compress`
- `priority` (hard task only): `1..5` (a signal that affects the simulation)

The observation includes:

- `vram_utilization` in `[0.0, 1.0]` (token-capacity proxy for VRAM/KV-cache)
- `incoming_tokens` (new load arriving this step)
- `memory_blocks`: each with `block_id`, `block_type`, `attention_score`, `token_count`, `age`
- `oom_triggered`, `message`, and OpenEnv-inherited `done` / `reward`

## Tasks

There are three deterministic task tiers:

- **Easy**: reduce utilization below `0.5` without OOM using `evict|retain`
- **Medium**: reduce below `0.4` while preserving critical blocks; `compress` is allowed
- **Hard**: survive a longer horizon with stability, retention, and a priority mechanism that can inject extra pressure when misused

## Quickstart (Local)

From the repo root (`meta_hackathon`):

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .\context_router
uvicorn context_router.server.app:app --host 0.0.0.0 --port 8000
```

Then verify core endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/tasks
curl -X POST http://localhost:8000/baseline
```

## Validation (Judge-Style)

Run tests:

```bash
.\.venv\Scripts\python.exe -m pytest context_router\tests -q
```

Run the baseline script:

```bash
.\.venv\Scripts\python.exe context_router\baseline\run_baseline.py --base-url http://localhost:8000
```

Validate the running environment contract:

```bash
cd context_router
openenv validate --url http://localhost:8000
```

Example results (March 31, 2026):

```text
pytest: 38 passed
baseline: easy=1.0000 medium=0.3657 hard=0.3721
openenv validate: passed=true (6/6 required checks)
```

## Scoring / Grading

The graders return a float in `[0.0, 1.0]` with partial credit. In general:

- **Easy** rewards reducing VRAM, surviving steps, and stability; penalizes OOM.
- **Medium** adds explicit retention credit (keeping `system_prompt` and high-attention blocks).
- **Hard** rewards survival, retention ratio, low average VRAM, and stability; penalizes OOM heavily.

Implementation:

- Environment: `context_router/server/context_env.py`
- Graders: `context_router/graders/grader_easy.py`, `context_router/graders/grader_medium.py`, `context_router/graders/grader_hard.py`
- Tasks metadata exposed at `/tasks`: `context_router/tasks/task_definitions.py`

## API Surface

Core OpenEnv endpoints (provided by `openenv-core` app wrapper):

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /schema`
- `GET /metadata`
- `GET /health`

Project-specific endpoints:

- `GET /tasks` (lists easy/medium/hard and their action schemas)
- `POST /grader` (scores a submitted trajectory)
- `POST /baseline` (runs an internal baseline policy and returns 3 scores)

## Repo Layout

- `context_router/`: primary environment implementation + tests
- `hf_deployment/`: deployment-oriented copy used for Hugging Face Spaces (Docker/metadata)
- `tests/`: miscellaneous verification scripts

## Rubric Mapping (Why This Scores Well)

- **Real-world utility**: models a real pain point in local LLM systems (KV-cache pressure and context management).
- **Task/grader quality**: deterministic, reproducible graders with partial credit and clear success criteria.
- **Environment design**: meaningful control problem with a non-trivial tradeoff: VRAM reduction vs retention of critical context.
- **Code/spec compliance**: passes `openenv validate`, has baseline script and an API-contract smoke test suite.
- **Creativity/novelty**: not another ticket-triage clone; focuses on inference-time systems behavior.

## More Docs

The Hugging Face Space card + environment-facing docs live here:

- `context_router/README.md`

