# RULES.md — OpenEnv Hackathon Hard Guardrails

> **Status:** IMMUTABLE HARD CONSTRAINTS — never override, never negotiate
> **Scope:** Every file, every function, every decision in this project
> **Enforcement:** AI co-pilot checks compliance before marking any code complete

---

## RULE CATEGORY 1 — OPENENV SPEC COMPLIANCE

These rules are directly derived from the OpenEnv framework API contract.
Violating any of them triggers automated disqualification.

### 1.1 Grader Scores

```python
# MANDATORY — every grader must end with this
return max(0.0, min(1.0, computed_score))
```

- ALL grader return values MUST be `float` type. Never `int`, never `None`.
- Grader scores MUST be in the closed interval `[0.0, 1.0]`.
- Graders MUST be deterministic: same episode trajectory → same score, always.
- Graders MUST produce partial credit: scores other than exactly 0.0 or 1.0 MUST
  be reachable for partial episodes.
- There MUST be at least 3 distinct graders: easy, medium, hard.

### 1.2 Data Models

```python
from pydantic import Field
from openenv.core.env_server.types import Action, Observation, State

class MyAction(Action):
    """Subclass Action from openenv.core.env_server.types"""
    command: str = Field(..., description="What to do")

class MyObservation(Observation):
    """Subclass Observation from openenv.core.env_server.types"""
    # NOTE: Observation base class already has `done: bool` and `reward: float`
    result: str = Field(..., description="What happened")
```

- Action MUST subclass `openenv.core.env_server.types.Action`
- Observation MUST subclass `openenv.core.env_server.types.Observation`
- Observation base class already provides `done` and `reward` fields — DO NOT redefine
- State MUST use `openenv.core.env_server.types.State` directly (has `episode_id` + `step_count`)
- `episode_id` MUST be a UUID string.
- `episode_id` MUST be regenerated fresh in every call to `reset()`.
- State MUST NOT carry over between episodes.

### 1.3 The reset() Method

- `reset()` MUST always succeed and return a valid Observation.
- `reset()` MUST be callable at any time — mid-episode, repeatedly, concurrently.
- `reset()` MUST accept an optional `seed` parameter for reproducibility.
- `reset()` MUST NOT raise any unhandled exception under any circumstance.
- `reset()` MUST regenerate `episode_id` using `str(uuid4())`.

### 1.4 The step() Method

```python
def step(self, action: MyAction) -> MyObservation:
    try:
        # all logic here
    except Exception as e:
        return MyObservation(
            result=str(e),
            success=False,
            done=True,
            reward=0.0
        )
```

- `step()` MUST NEVER raise an unhandled exception. Ever.
- `step()` MUST eventually set `done=True` (no infinite episodes).
- `step()` MUST return a valid Observation even when given malformed input.
- Observation is the return type (NOT StepResult — StepResult is client-side).
- Reward values in Observation MUST be floats.

### 1.5 The state Property

```python
@property
def state(self) -> State:
    return self._state
```

- `state` is a **@property**, NOT a method. Do not call it with `()`.

### 1.6 The Server (app.py)

```python
from openenv.core.env_server import create_app

# CORRECT — pass the CLASS, not an instance
app = create_app(MyEnvironment, MyAction, MyObservation, env_name="my_env")
```

- MUST use `create_app()` from `openenv.core.env_server`
  - NOT `create_fastapi_app()` (does not exist)
- MUST pass the Environment **class** (or factory function), NOT an instance
  - Each WebSocket session gets its own environment instance
- The server communicates via WebSocket at `/ws` for persistent sessions

### 1.7 openenv.yaml

- `openenv.yaml` MUST exist at the project root.
- MUST declare: env name, version, description, schema version.
- MUST enumerate ALL tasks by name and difficulty level.
- MUST include action and observation schema definitions.
- Run `openenv validate --verbose` before EVERY push to HF Spaces.

### 1.8 The Three Required Custom Endpoints

```
/tasks    → returns list of tasks + action schema for each
/grader   → returns float score after episode completes
/baseline → triggers inference script, returns scores for all 3 tasks
```

- ALL three MUST exist and return valid responses.
- `/baseline` MUST return scores even if one task's grader fails (return 0.0 for that task).
- `/grader` response MUST include the `float` score, NOT just an HTTP status.
- `/tasks` response MUST include action schema fields for each task.

---

## RULE CATEGORY 2 — DOCKERFILE & DEPLOYMENT

### 2.1 Base Image

```dockerfile
# CORRECT — multi-stage build
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder

# FORBIDDEN
FROM python:3.11
FROM python:3.11-slim
FROM ubuntu:22.04
```

- Dockerfile MUST start from `openenv-base` image via `ARG BASE_IMAGE`.
- Using any other base image is FORBIDDEN.

### 2.2 Dependencies

- `pyproject.toml` is the PRIMARY dependency spec (not requirements.txt)
- `requirements.txt` can be auto-generated from pyproject.toml for Docker
- Dependencies SHOULD have pinned versions
- GPU-dependent libraries are FORBIDDEN:
  ```
  torch               ← FORBIDDEN (GPU version)
  tensorflow          ← FORBIDDEN
  cuda-*              ← FORBIDDEN
  ```
- Docker image MUST build with `openenv build`.
- Docker image MUST run without mounting any local volumes.
- Dockerfile uses `uv sync` for dependency installation (not pip).

### 2.3 Python Version

- Python version MUST be 3.10, 3.11, or 3.12 ONLY.
- Python 3.13+ is FORBIDDEN (not supported by OpenEnv).
- Python 3.9 and below are FORBIDDEN (typing compatibility).

### 2.4 HuggingFace Space

- HF Space MUST return HTTP 200 on `/health` check at all times.
- HF Space MUST respond to `POST /reset` without error.
- HF Space MUST support WebSocket at `/ws`.
- HF Space URL MUST be stable (no custom domain required; HF default is fine).
- HF Space MUST be public (not private/gated).
- Deploy with `openenv push [--repo-id <repo>]`.

---

## RULE CATEGORY 3 — BASELINE SCRIPT

### 3.1 CLI Interface

```python
# MANDATORY
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True,
                    help='Base URL of the deployed environment')
args = parser.parse_args()
```

- `--base-url` argument MUST be implemented and MUST be required.
- Hardcoding `localhost` or any URL in the baseline script is FORBIDDEN.

### 3.2 Exit Behavior

- Script MUST exit with code `0` on success.
- Script MUST print scores for all 3 tasks to stdout.
- Script MUST NOT error out on a single task failure — catch exceptions per-task
  and return `0.0` for that task's score, then continue.
- Script MUST complete within a reasonable timeout (< 5 minutes total).

### 3.3 Output Format

```python
# Minimum required output
print(f"Task easy score:   {score_easy:.4f}")
print(f"Task medium score: {score_medium:.4f}")
print(f"Task hard score:   {score_hard:.4f}")
```

- Output MUST be parseable — one score per line, labeled by task name.
- Scores printed MUST match what graders return.

### 3.4 Client Usage

```python
# Baseline script SHOULD use the EnvClient (WebSocket) for communication
from my_env import MyEnv, MyAction

with MyEnv(base_url=args.base_url).sync() as client:
    result = client.reset()
    # ... run episode
```

- Baseline script SHOULD use the WebSocket EnvClient (sync mode)
- Alternatively, HTTP requests are acceptable for simplicity

---

## RULE CATEGORY 4 — ERROR HANDLING

### 4.1 No Silent Failures

```python
# FORBIDDEN — silent failure
try:
    ...
except:
    pass

# FORBIDDEN — bare except with pass
except Exception:
    pass

# REQUIRED — always log and surface the error
except Exception as e:
    logger.error(f"step() error: {e}")
    return MyObservation(result=str(e), success=False, done=True, reward=0.0)
```

- `try: ... except: pass` is FORBIDDEN in all project files.
- All exceptions in `step()` MUST produce a valid Observation with `done=True`.
- All exceptions in graders MUST be caught and return `0.0` (not re-raised).
- All exceptions in `/baseline` endpoint MUST be caught per-task.

### 4.2 Input Validation

- `step()` MUST handle malformed, empty, null, and out-of-range action inputs.
- `step()` MUST NOT assume any field of the incoming action is within expected range.
- All string inputs MUST be sanitized for length before processing.

---

## RULE CATEGORY 5 — REPRODUCIBILITY

### 5.1 Seeding

```python
def reset(self, seed: Optional[int] = None) -> MyObservation:
    if seed is not None:
        self._rng = random.Random(seed)
        # also seed numpy if used: np.random.seed(seed)
    self._state = State(episode_id=str(uuid4()), step_count=0)
    ...
```

- ALL randomness in the environment MUST be seeded via `reset(seed=N)`.
- Calling `reset(seed=42)` twice MUST produce identical episodes.
- Unseeded resets MAY produce random episodes (default behavior is acceptable).

### 5.2 Determinism

- Docker image MUST produce identical results on repeated runs given same seed.
- Graders MUST be pure functions of their input trajectory (no external state).
- `/baseline` endpoint results MUST be reproducible across calls.

---

## RULE CATEGORY 6 — DOCUMENTATION

### 6.1 README Requirements (MANDATORY sections)

```markdown
# [Environment Name]
## Overview
## Action Space
| Field | Type | Values | Description |
## Observation Space
| Field | Type | Description |
## Tasks
| Task | Difficulty | Description | Success Condition |
## Reward Function
## Setup Instructions
## Example Episode
```

- README MUST exist and contain ALL six sections above.
- Action space table MUST document every field of the Action dataclass.
- Observation space table MUST document every field of the Observation dataclass.
- Reward function section MUST include the actual formula (not just a description).
- Example episode MUST show actual Python code using the EnvClient.

---

## RULE CATEGORY 7 — TASK DESIGN

### 7.1 Task Count and Structure

- There MUST be exactly 3+ tasks: easy, medium, hard.
- Each task MUST have a distinct action schema (NOT identical for all tasks).
- Difficulty MUST be truly progressive:
  - Easy: random agent achieves > 0.0 score ~30% of the time
  - Medium: random agent achieves > 0.0 score ~5–10% of the time
  - Hard: random agent achieves > 0.0 score < 1% of the time

### 7.2 Domain Constraints

- Domain MUST be real-world relevant (not a classic game or toy).
- Domain MUST be simulable in pure Python with no external API calls in `step()`.
- Domain MUST NOT require a GPU in the Docker container.

### 7.3 Action Schema

- Actions MUST use structured schemas (typed Pydantic fields), not free-text strings.
- Each task's action schema MUST be documented in `/tasks` response AND in `openenv.yaml`.
- Action types MUST be validated in `step()` before processing.

---

## RULE CATEGORY 8 — FORBIDDEN PATTERNS

The following patterns are FORBIDDEN in all project code:

```python
# FORBIDDEN: Bare except / silent failure
except: pass
except Exception: pass

# FORBIDDEN: Hardcoded URLs
base_url = "http://localhost:8000"
base_url = "https://my-fixed-space.hf.space"

# FORBIDDEN: Grader returning int
return 1   # ← must be return 1.0

# FORBIDDEN: Binary reward only
if success:
    return 1.0
else:
    return 0.0
# ↑ Must have intermediate partial credit formula

# FORBIDDEN: GPU libraries in requirements
torch==2.0.0+cu117
tensorflow-gpu

# FORBIDDEN: Python version outside supported range
FROM python:3.13   # unsupported
FROM python:3.9    # too old

# FORBIDDEN: Infinite episodes
def step(self, action):
    # ... never sets done=True

# FORBIDDEN: Wrong OpenEnv types
class StepResult:  # ← do not redefine — use openenv.core types
class Action:      # ← do not redefine — subclass from openenv.core

# FORBIDDEN: Wrong server creation
create_fastapi_app(env, ...)  # ← does not exist
create_app(MyEnvironment(), ...)  # ← do not pass instance, pass CLASS

# FORBIDDEN: state as method
def state(self):  # ← must be @property, not def
```

---

## COMPLIANCE CHECKLIST (run before marking any PR complete)

```
□ All grader return values are float, clipped to [0.0, 1.0]
□ step() has no bare raise statements
□ step() has no bare except: pass
□ episode_id is UUID string, regenerated in every reset()
□ done=True is reachable within step logic
□ baseline script accepts --base-url argument
□ baseline script exits 0 on success
□ baseline prints scores for all 3 tasks
□ Dockerfile uses openenv-base image (via ARG BASE_IMAGE)
□ pyproject.toml lists all dependencies
□ No GPU libraries in dependencies
□ openenv.yaml declares all tasks, endpoints, schema version
□ README has all 6 required sections
□ /tasks returns 3+ tasks with action schemas
□ /grader returns float score
□ /baseline returns scores even if one task fails
□ All 3 action schemas are distinct from each other
□ openenv validate --verbose shows 0 errors
□ openenv build completes successfully
□ HF Space /health returns 200
□ create_app() receives CLASS, not instance
□ state is a @property
□ Observation subclasses openenv.core.env_server.types.Observation
□ Action subclasses openenv.core.env_server.types.Action
```