# IMPLEMENTATION_ROADMAP.md — Step-by-Step for Both Developers
> **Project:** Edge GPU Context Memory Router — Meta PyTorch Hackathon
> **Deadline:** April 7, 2026 — 11:59 PM IST
> **Structure:** Chronological phases, with exact file names, who does what, and when to merge.

---

## READING GUIDE

- 🔵 **Dev 1 (Shreyas)** — owns the environment core
- 🟢 **Dev 2 (Samarth)** — owns graders, server API, baseline, README
- 🟡 **Both together** — must be done on a shared call
- `[MERGE]` — a defined point where branches combine into `main`
- `[GATE]` — hard stop; next phase does NOT begin until this passes

---

## PHASE 0 — DAY 1 SETUP (Both, Together, ~2 hours)

> Do this entire phase together before splitting. **No code is written without completing this phase.**

### Step 0.1 🟡 — Repository Setup

```bash
# One person initializes the repo (Dev 1 recommended)
cd meta_hackathon

# Install openenv-core and tools
python -m venv .venv
.venv\Scripts\activate               # Windows
pip install openenv-core fastapi uvicorn pydantic huggingface_hub pyright

# Initialize the environment scaffold
openenv init context_router
# This creates the folder: context_router/

# Verify scaffold
cd context_router
openenv --help

# Confirm .gitignore exists (or create it):
# .venv/ __pycache__/ *.pyc .env *.egg-info/ dist/ .DS_Store outputs/ *.log
git add .gitignore
git commit -m "[both] chore: init repo and openenv scaffold"
git push origin main
```

### Step 0.2 🟡 — Agree on Domain Design

Fill out `DOMAIN_DESIGN_TEMPLATE.md` together. You must agree on and write down:
- What the 3 tasks are (easy / medium / hard)
- What the action fields are (exact names, types, valid ranges)
- What the observation fields are (exact names, types)
- What "success" means for each task (in plain English)
- The reward formula for each task (write the math, not just words)

**Do NOT proceed to Step 0.3 until every field in this template is filled.**

### Step 0.3 🟡 — Write and Lock `models.py`

**File:** `context_router/models.py`

Both write this together. It defines the frozen interface contract for the whole project.

```python
# context_router/models.py — FROZEN AFTER THIS COMMIT
from enum import Enum
from typing import List
from pydantic import Field
from openenv.core.env_server.types import Action, Observation

class EvictionTactic(str, Enum):
    EVICT    = "evict"
    RETAIN   = "retain"
    COMPRESS = "compress"   # used only in medium/hard tasks

class CacheAction(Action):
    target_block_id: int = Field(..., description="Index of memory block to act on")
    tactic: EvictionTactic = Field(..., description="What action to perform on the block")
    # Hard task only — add priority: int here if needed

class MemoryBlockInfo:
    block_id: int
    block_type: str
    attention_score: float
    token_count: int
    age: int

class CacheObservation(Observation):
    # DO NOT add done or reward — they are inherited
    vram_utilization: float = Field(..., description="VRAM used / VRAM max, range [0.0, 1.0]")
    incoming_tokens:  int   = Field(..., description="Token queue size at this step")
    memory_blocks:    List  = Field(default_factory=list, description="Current memory block states")
    oom_triggered:    bool  = Field(default=False, description="True if OOM event occurred this step")
    message:          str   = Field(default="", description="Human-readable status message")
```

After writing:
```bash
# Validate immediately
openenv validate --verbose   # must show 0 errors

# Commit together
git add context_router/models.py context_router/openenv.yaml
git commit -m "[both] feat: lock data contract — models.py v1"
git tag schema-v1
git push origin main --tags
```

### `[GATE 0]` — Schema Lock Gate

```
□ schema-v1 tag exists on main
□ openenv validate shows 0 errors
□ Both developers have read and agreed on models.py field names
□ Both developers can state from memory: CacheAction fields, CacheObservation fields
```
**Nothing in Phase 1 or Phase 2 begins until all boxes are checked.**

---

## PHASE 1 — PARALLEL DEVELOPMENT (Both work simultaneously)

> After Gate 0, **Dev 1 and Dev 2 work in parallel on separate branches.** They do NOT block each other.

```bash
# Dev 1 creates their branch
git checkout -b dev1/env-core

# Dev 2 creates their branch
git checkout -b dev2/graders-baseline
```

---

### DEV 1 TRACK — Environment Core

#### Step 1.1 🔵 — Implement `context_env.py` skeleton

**File:** `context_router/server/context_env.py`

Start with the class skeleton before any task logic:

```python
# context_router/server/context_env.py
import logging
import random
from uuid import uuid4
from typing import Optional, List
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from ..models import CacheAction, CacheObservation, MemoryBlockInfo

logger = logging.getLogger(__name__)

class ContextRouterEnv(Environment):
    MAX_STEPS = 50
    VRAM_MAX  = 16.0   # GB

    def __init__(self):
        self._rng       = random.Random()
        self._state     = State(episode_id=str(uuid4()), step_count=0)
        self._vram_used = 0.0
        self._blocks    = []

    @property
    def state(self) -> State:          # @property MUST be here — never def state(self):
        return self._state

    def reset(self, seed: Optional[int] = None) -> CacheObservation:
        # IMPLEMENT IN STEP 1.2
        ...

    def step(self, action: CacheAction) -> CacheObservation:
        # IMPLEMENT IN STEP 1.3 (Task 1), 1.4 (Task 2), 1.5 (Task 3)
        ...
```

**Test:** Run this import to confirm no syntax errors:
```bash
python -c "from context_router.server.context_env import ContextRouterEnv; print('OK')"
```

#### Step 1.2 🔵 — Implement `reset()`

Still in `context_router/server/context_env.py`:

```python
def reset(self, seed: Optional[int] = None) -> CacheObservation:
    if seed is not None:
        self._rng = random.Random(seed)
    # Fresh episode_id every reset — NEVER reuse the old one
    self._state     = State(episode_id=str(uuid4()), step_count=0)
    self._vram_used = self._rng.uniform(0.3, 0.7) * self.VRAM_MAX
    self._blocks    = self._generate_initial_blocks()
    return CacheObservation(
        vram_utilization=self._vram_used / self.VRAM_MAX,
        incoming_tokens=self._rng.randint(50, 300),
        memory_blocks=[b.__dict__ for b in self._blocks],
        oom_triggered=False,
        message="Environment reset. Ready.",
        done=False,
        reward=0.0
    )
```

**Test** (run from project root):
```bash
python -c "
from context_router.server.context_env import ContextRouterEnv
env = ContextRouterEnv()
obs1 = env.reset(seed=42)
obs2 = env.reset(seed=42)
assert obs1.vram_utilization == obs2.vram_utilization, 'FAIL: not deterministic'
assert obs1.done == False, 'FAIL: done should be False on reset'
print('reset() PASSED')
"
```

**Commit after this test passes:**
```bash
git add context_router/server/context_env.py
git commit -m "[dev1] feat: implement reset() — deterministic, fresh episode_id"
```

**Immediately notify Dev 2:** *"reset() is done. Stub grader is below — use it."*
```python
# graders/grader_easy_stub.py — Dev 1 provides this
def grader_easy_stub(trajectory: list) -> float:
    """STUB. Real grader is yours. Returns 0.5 always."""
    return 0.5
```

#### Step 1.3 🔵 — Implement `step()` for Task 1 (Easy)

Still in `context_router/server/context_env.py`.

Implement the full try/except wrapped step logic for the Easy task only:

```python
def step(self, action: CacheAction) -> CacheObservation:
    try:
        # Increment step counter
        self._state = State(
            episode_id=self._state.episode_id,
            step_count=self._state.step_count + 1
        )
        # Max steps enforcement
        if self._state.step_count >= self.MAX_STEPS:
            return CacheObservation(..., done=True, reward=self._partial_credit())

        # Validate action
        if action.target_block_id < 0 or action.target_block_id >= len(self._blocks):
            return CacheObservation(..., message="invalid block_id", done=True, reward=0.0)

        # Task logic here...
        reward = self._compute_reward_easy(action)
        done   = self._vram_used / self.VRAM_MAX < 0.5 or self._state.step_count >= self.MAX_STEPS

        return CacheObservation(
            vram_utilization=self._vram_used / self.VRAM_MAX,
            incoming_tokens=self._rng.randint(50, 300),
            memory_blocks=[b.__dict__ for b in self._blocks],
            oom_triggered=self._oom_event,
            message="ok",
            done=done,
            reward=float(reward)
        )
    except Exception as e:
        logger.error(f"step() error: {e}", exc_info=True)
        return CacheObservation(
            vram_utilization=0.0, incoming_tokens=0,
            memory_blocks=[], oom_triggered=False,
            message=f"error: {e}", done=True, reward=0.0
        )
```

**Run the Dev 1 standalone test suite** (`tests/test_env_standalone.py`):
```bash
python tests/test_env_standalone.py   # all assertions must pass
```

**Commit:**
```bash
git add context_router/server/context_env.py tests/test_env_standalone.py
git commit -m "[dev1] feat: step() Task 1 (easy) complete — standalone tests pass"
```

**Notify Dev 2:** *"Task 1 step() is ready. Use the real env now for grader_easy testing."*

#### Step 1.4 🔵 — Implement `step()` for Tasks 2 & 3 (Medium, Hard)

Same pattern as Step 1.3. Add task-routing logic:

```python
def step(self, action: CacheAction) -> CacheObservation:
    task = self._current_task   # set by a set_task("easy"|"medium"|"hard") method or in reset()
    try:
        ...
        if task == "easy":   reward = self._compute_reward_easy(action)
        elif task == "medium": reward = self._compute_reward_medium(action)
        elif task == "hard":   reward = self._compute_reward_hard(action)
        ...
```

**After each task:** run tests, commit individually, notify Dev 2.

```bash
git commit -m "[dev1] feat: step() Task 2 (medium) complete"
git commit -m "[dev1] feat: step() Task 3 (hard) complete"
```

#### Step 1.5 🔵 — Update `openenv.yaml`

**File:** `context_router/openenv.yaml`

Run after every change to `models.py` or task definitions:
```bash
openenv validate --verbose   # confirm 0 errors after every yaml edit
git add context_router/openenv.yaml
git commit -m "[dev1] sync: openenv.yaml updated to match step() task definitions"
```

#### Step 1.6 🔵 — Dev 1 Push & Signal for Merge

```bash
git push origin dev1/env-core
# Message Dev 2: "dev1/env-core is ready for merge ceremony. All standalone tests pass."
```

---

### DEV 2 TRACK — Graders, Server, Baseline, README

> **While Dev 1 works on Steps 1.1–1.6, Dev 2 works on these steps in parallel.**

#### Step 2.1 🟢 — Write Stub Graders + Tests (no live env needed)

**Files to create:**
- `context_router/graders/__init__.py` (empty)
- `context_router/graders/grader_easy.py`
- `context_router/graders/grader_medium.py`
- `context_router/graders/grader_hard.py`
- `context_router/tests/__init__.py` (empty)
- `context_router/tests/test_grader_easy.py`
- `context_router/tests/test_grader_medium.py`
- `context_router/tests/test_grader_hard.py`

Start with stubs:

```python
# context_router/graders/grader_easy.py
import logging
logger = logging.getLogger(__name__)

def grader_easy(trajectory: list) -> float:
    """STUB — replace with real logic in Step 2.2"""
    try:
        if not trajectory:
            return 0.0
        return 0.5   # stub
    except Exception as e:
        logger.error(f"grader_easy error: {e}")
        return 0.0
```

Write tests that the stub should already pass:

```python
# context_router/tests/test_grader_easy.py
from context_router.graders.grader_easy import grader_easy

PERFECT  = [{"vram_utilization": 0.3, "oom_triggered": False, "reward": 1.0, "done": True}]
EMPTY    = []
PARTIAL  = [
    {"vram_utilization": 0.8, "oom_triggered": True,  "reward": 0.2, "done": False},
    {"vram_utilization": 0.5, "oom_triggered": False, "reward": 0.7, "done": True},
]

def test_empty_returns_zero():
    assert grader_easy(EMPTY) == 0.0

def test_returns_float():
    assert isinstance(grader_easy(PERFECT), float)

def test_clamped():
    score = grader_easy(PERFECT)
    assert 0.0 <= score <= 1.0

def test_deterministic():
    assert grader_easy(PARTIAL) == grader_easy(PARTIAL)

# These will fail with stub (0.5 ≠ 1.0, 0.5 is not between) — fix in Step 2.2
def test_perfect_returns_one():
    assert grader_easy(PERFECT) == 1.0

def test_partial_between():
    s = grader_easy(PARTIAL)
    assert 0.0 < s < 1.0
```

```bash
python -m pytest context_router/tests/test_grader_easy.py -v
# 4 pass (type/clamp/empty/deterministic), 2 fail (perfect/partial) — this is EXPECTED
git add context_router/graders/ context_router/tests/
git commit -m "[dev2] feat: stub graders + test scaffolding (4/6 tests pass as expected)"
```

#### Step 2.2 🟢 — Implement Real Grader Logic (after Dev 1 finishes Step 1.3)

Once Dev 1 signals Task 1 step() is ready, replace stub with real logic:

```python
# context_router/graders/grader_easy.py
import logging
logger = logging.getLogger(__name__)

def grader_easy(trajectory: list) -> float:
    """
    Easy task: reduce VRAM below 50% within 50 steps without OOM.
    Score bands:
      1.0   → VRAM < 0.5 AND no OOM events
      0.5–1 → VRAM < 0.5 but some OOM events
      0.1–0.5 → VRAM reduced but not below 0.5
      0.0   → empty or no improvement
    """
    try:
        if not trajectory:
            return 0.0

        final_obs    = trajectory[-1]
        vram_final   = final_obs.vram_utilization if hasattr(final_obs, 'vram_utilization') else final_obs.get('vram_utilization', 1.0)
        oom_events   = sum(1 for obs in trajectory if (obs.oom_triggered if hasattr(obs, 'oom_triggered') else obs.get('oom_triggered', False)))

        # Base: how much did VRAM drop? Lower is better.
        vram_score    = max(0.0, 1.0 - (vram_final / 0.5)) if vram_final < 0.5 else 0.0
        oom_penalty   = 0.1 * oom_events
        steps_taken   = len(trajectory)
        speed_bonus   = 0.1 if steps_taken < 25 else 0.0

        score = vram_score * 0.8 + speed_bonus - oom_penalty
        return float(max(0.0, min(1.0, score)))

    except Exception as e:
        logger.error(f"grader_easy error: {e}")
        return 0.0
```

**Run tests — all 6 must now pass:**
```bash
python -m pytest context_router/tests/test_grader_easy.py -v
# 6/6 PASS — commit only after this
git add context_router/graders/grader_easy.py
git commit -m "[dev2] feat: grader_easy real logic — 6/6 tests pass, partial credit verified"
```

Repeat for `grader_medium.py` and `grader_hard.py` following the same TDD pattern.

```bash
git commit -m "[dev2] feat: grader_medium — 6/6 tests pass"
git commit -m "[dev2] feat: grader_hard — 6/6 tests pass"
```

#### Step 2.3 🟢 — Implement `task_definitions.py`

**File:** `context_router/tasks/task_definitions.py`

```python
# context_router/tasks/task_definitions.py
TASKS = {
    "easy": {
        "name": "easy",
        "description": "Reduce VRAM below 50% without triggering OOM.",
        "action_schema": {
            "target_block_id": {"type": "int", "description": "Index of memory block"},
            "tactic":          {"type": "string", "values": ["evict", "retain"]}
        }
    },
    "medium": {
        "name": "medium",
        "description": "Reduce VRAM below 40% while keeping high-attention blocks.",
        "action_schema": {
            "target_block_id": {"type": "int", "description": "Index of memory block"},
            "tactic":          {"type": "string", "values": ["evict", "retain", "compress"]}
        }
    },
    "hard": {
        "name": "hard",
        "description": "Optimize VRAM under OOM pressure with a priority queue constraint.",
        "action_schema": {
            "target_block_id": {"type": "int",    "description": "Index of memory block"},
            "tactic":          {"type": "string",  "values": ["evict", "retain", "compress"]},
            "priority":        {"type": "int",     "description": "Eviction priority (1=highest)"}
        }
    }
}
```

> **Rule:** Notify Dev 1 of the task names here — they must match `openenv.yaml`.

```bash
git add context_router/tasks/
git commit -m "[dev2] feat: task_definitions.py — 3 tasks with distinct schemas"
```

#### Step 2.4 🟢 — Implement `app.py`

**File:** `context_router/server/app.py`

```python
# context_router/server/app.py
import logging
from openenv.core.env_server import create_app
from .context_env import ContextRouterEnv
from ..models import CacheAction, CacheObservation
from ..graders.grader_easy   import grader_easy
from ..graders.grader_medium import grader_medium
from ..graders.grader_hard   import grader_hard
from ..tasks.task_definitions import TASKS

logger = logging.getLogger(__name__)

# CORRECT: pass CLASS, never instance
app = create_app(ContextRouterEnv, CacheAction, CacheObservation, env_name="context_router")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks")
def get_tasks():
    return {"tasks": list(TASKS.values())}

@app.post("/grader")
def grader_endpoint(trajectory: list):
    task = trajectory[0].get("task", "easy") if trajectory else "easy"
    grader_fn = {"easy": grader_easy, "medium": grader_medium, "hard": grader_hard}.get(task, grader_easy)
    try:
        score = grader_fn(trajectory)
        return {"score": float(score)}
    except Exception as e:
        logger.error(f"/grader error: {e}")
        return {"score": 0.0}

@app.post("/baseline")
def baseline_endpoint():
    results = {}
    for task_name in ["easy", "medium", "hard"]:
        try:
            results[task_name] = float(_run_baseline_episode(task_name))
        except Exception as e:
            logger.error(f"baseline task {task_name} failed: {e}")
            results[task_name] = 0.0
    return results

def _run_baseline_episode(task_name: str) -> float:
    # Run a short random episode and return its grader score
    env = ContextRouterEnv()
    env.reset(seed=42)
    trajectory = []
    from ..models import EvictionTactic
    import random
    rng = random.Random(42)
    for _ in range(10):
        action = CacheAction(target_block_id=rng.randint(0, 2), tactic=EvictionTactic.EVICT)
        obs = env.step(action)
        trajectory.append(obs)
        if obs.done:
            break
    grader_fn = {"easy": grader_easy, "medium": grader_medium, "hard": grader_hard}[task_name]
    return grader_fn(trajectory)
```

```bash
git add context_router/server/app.py
git commit -m "[dev2] feat: app.py — all 5 endpoints implemented"
```

#### Step 2.5 🟢 — Implement `baseline/run_baseline.py`

**File:** `baseline/run_baseline.py`

```python
#!/usr/bin/env python3
"""
Baseline runner for the Context Router OpenEnv environment.
Usage: python baseline/run_baseline.py --base-url https://<your-space>.hf.space
"""
import argparse
import sys
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_task(base_url: str, task_name: str) -> float:
    """Run one episode via HTTP and call /grader."""
    # Reset
    reset_resp = requests.post(f"{base_url}/reset", timeout=30)
    reset_resp.raise_for_status()

    # Run a simple baseline episode (random actions)
    trajectory = []
    for step in range(15):
        action_payload = {"target_block_id": step % 3, "tactic": "evict", "task": task_name}
        step_resp = requests.post(f"{base_url}/step", json=action_payload, timeout=30)
        step_resp.raise_for_status()
        obs = step_resp.json()
        trajectory.append(obs)
        if obs.get("done", False):
            break

    # Score
    grade_resp = requests.post(f"{base_url}/grader", json=trajectory, timeout=30)
    grade_resp.raise_for_status()
    return float(grade_resp.json()["score"])

def main():
    parser = argparse.ArgumentParser(description="Baseline runner")
    parser.add_argument("--base-url", required=True, help="Base URL of deployed environment")
    args = parser.parse_args()

    scores = {}
    for task in ["easy", "medium", "hard"]:
        try:
            logger.info(f"Running task: {task}")
            scores[task] = run_task(args.base_url, task)
        except Exception as e:
            logger.error(f"Task {task} failed: {e}", exc_info=True)
            scores[task] = 0.0

    print(f"Task easy score:   {scores['easy']:.4f}")
    print(f"Task medium score: {scores['medium']:.4f}")
    print(f"Task hard score:   {scores['hard']:.4f}")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Test:**
```bash
# Test only after Dev 1's server is running locally
uvicorn context_router.server.app:app --port 8000 &
python baseline/run_baseline.py --base-url http://localhost:8000
# → must print 3 float scores and exit 0
grep -n "localhost" baseline/run_baseline.py   # must return NOTHING
```

```bash
git add baseline/run_baseline.py
git commit -m "[dev2] feat: baseline script — --base-url, per-task exception handling, exits 0"
```

#### Step 2.6 🟢 — Write README

**File:** `README.md`

All 6 sections required. Fill them with actual content from the domain design:

```markdown
# Context Router — OpenEnv Environment

## Overview
...

## Action Space
| Field | Type | Valid Values | Description |
...

## Observation Space
| Field | Type | Description |
...

## Tasks
| Task | Difficulty | Description | Success Condition |
...

## Reward Function
reward_easy = (vram_reduction_score × 0.8) + speed_bonus − (0.1 × oom_events)
...

## Setup Instructions
...

## Example Episode
[real Python code using EnvClient]
```

```bash
git add README.md
git commit -m "[dev2] feat: README complete — all 6 sections with real formulas and code"
```

#### Step 2.7 🟢 — Dev 2 Push & Signal for Merge

```bash
git push origin dev2/graders-baseline
# Message Dev 1: "dev2/graders-baseline is ready. All grader tests pass. Baseline exits 0."
```

---

## `[MERGE POINT 1]` — Integration Merge (Both, Together, ~1 hour)

> **Trigger:** Dev 1 signals env-core ready AND Dev 2 signals graders-baseline ready.
> This is the first merge ceremony. Both must be on a call.

```bash
# Step 1: Run Dev 1 standalone tests
python tests/test_env_standalone.py   # must print "All Dev 1 standalone tests passed ✓"

# Step 2: Run Dev 2 grader tests
python -m pytest context_router/tests/ -v   # all 18 tests (6 per grader) must pass

# Step 3: Import smoke test
python -c "
from context_router.server.context_env import ContextRouterEnv
from context_router.models import CacheAction, EvictionTactic
env = ContextRouterEnv()
obs = env.reset(seed=42)
print('vram:', obs.vram_utilization)
print('blocks:', len(obs.memory_blocks))
print('IMPORT TEST PASSED')
"
# If this fails → field names have drifted. Fix models.py TOGETHER before continuing.

# Step 4: Run one real trajectory through grader_easy
python -c "
from context_router.server.context_env import ContextRouterEnv
from context_router.graders.grader_easy import grader_easy
from context_router.models import CacheAction, EvictionTactic

env = ContextRouterEnv()
env.reset(seed=42)
trajectory = []
for i in range(5):
    obs = env.step(CacheAction(target_block_id=i % 3, tactic=EvictionTactic.EVICT))
    trajectory.append(obs)
score = grader_easy(trajectory)
print(type(score), score)
assert isinstance(score, float), 'FAIL: not float'
assert 0.0 <= score <= 1.0, 'FAIL: out of range'
print('GRADER INTEGRATION TEST PASSED')
"

# Step 5: Start local server and hit endpoints
uvicorn context_router.server.app:app --port 8000 &
sleep 3
curl http://localhost:8000/health              # 200 OK
curl http://localhost:8000/tasks              # 3 tasks with distinct schemas
curl -X POST http://localhost:8000/reset      # valid JSON Observation

# Step 6: Run baseline script
python baseline/run_baseline.py --base-url http://localhost:8000
# exits 0, prints 3 scores

# Step 7: openenv validate
openenv validate --verbose   # 0 errors

# Step 8: Merge to main
git checkout main
git merge dev1/env-core
git merge dev2/graders-baseline
git push origin main
git tag merge-integration-$(date +%Y%m%d)
```

### `[GATE 1]` — Integration Gate

```
□ Import smoke test passes
□ grader_easy returns float from real trajectory
□ /health → 200
□ /tasks → 3 tasks, schemas differ
□ /reset → valid JSON
□ baseline script exits 0, 3 scores printed
□ openenv validate → 0 errors
□ MISTAKES.md updated with this session entry
```
**Phase 3 does NOT begin until all boxes are checked.**

---

## PHASE 2 — DOCKER & DEPLOYMENT (Dev 2 leads, Dev 1 supports)

> After Gate 1. Both on a call for key steps.

#### Step 3.1 🟢 — Write/Verify `Dockerfile`

**File:** `context_router/Dockerfile`  
*(the `openenv init` scaffold provides this — verify, don't rewrite)*

```dockerfile
ARG BASE_IMAGE=openenv-base:latest      # NEVER change this line
FROM ${BASE_IMAGE} AS builder
WORKDIR /app
COPY pyproject.toml .
RUN uv sync                              # never pip install — always uv sync
COPY . .
EXPOSE 8000
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1
CMD ["uvicorn", "context_router.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 3.2 🟢 — Verify `pyproject.toml`

**File:** `context_router/pyproject.toml`

```toml
[project]
name = "context-router"
version = "0.1.0"
requires-python = ">=3.10,<3.13"

dependencies = [
    "openenv-core",
    "fastapi",
    "uvicorn",
    "pydantic",
    "requests",
]
# NO torch, NO tensorflow, NO cuda-anything
```

```bash
# Grep for forbidden libs before committing
grep -n "torch\|cuda\|tensorflow" context_router/pyproject.toml   # must return nothing
```

#### Step 3.3 🟡 — Build Docker Image

```bash
cd context_router
openenv build
# Must exit 0 with no errors
```

If it fails:
- Python version error → check `pyproject.toml` `requires-python`
- Missing dependency → add to `pyproject.toml` (NOT requirements.txt)
- Import error → fix the import path in the failing file

#### Step 3.4 🟡 — Full Container Test

```bash
# Run the container
docker run -d -p 8000:8000 openenv-context_router
sleep 5

# Hit every required endpoint
curl http://localhost:8000/health              # 200 + {"status":"ok"}
curl http://localhost:8000/tasks              # 3 tasks, distinct schemas
curl -X POST http://localhost:8000/reset      # CacheObservation JSON
curl -X POST http://localhost:8000/grader     # {"score": X.X}
curl -X POST http://localhost:8000/baseline   # {easy: X, medium: X, hard: X}

# Run baseline script
python baseline/run_baseline.py --base-url http://localhost:8000
# exits 0, 3 scores

# Validate spec
openenv validate --verbose   # 0 errors
```

**Commit everything:**
```bash
git add context_router/Dockerfile context_router/pyproject.toml
git commit -m "[both] chore: Dockerfile and pyproject.toml verified — openenv build passes"
git push origin main
```

#### Step 3.5 🟡 — Deploy to HuggingFace Spaces

```bash
# Authenticate (one-time)
huggingface-cli login   # paste token from https://huggingface.co/settings/tokens

# Deploy
cd context_router
openenv push
# Note the HF Space URL printed here: ___________________________________
```

#### Step 3.6 🟡 — Verify Live Deployment

```bash
HF_URL="https://<your-space>.hf.space"   # replace with actual URL

# Wait for Space to boot (~30s)
sleep 30

curl ${HF_URL}/health                                          # must be 200
curl -X POST ${HF_URL}/reset                                   # must return JSON
python baseline/run_baseline.py --base-url ${HF_URL}           # exits 0, 3 scores
openenv validate --verbose --url ${HF_URL}                     # 0 errors
```

### `[GATE 2]` — Deployment Gate

```
□ openenv build exits 0
□ Docker container /health returns 200
□ All 5 endpoints respond correctly from container
□ baseline script exits 0 from container
□ openenv validate passes from container
□ HF Space /health returns 200
□ baseline script exits 0 against live HF Space URL
□ openenv validate passes against live HF Space URL
```

---

## PHASE 3 — POLISH & SUBMISSION (Both, Together)

#### Step 4.1 🟡 — README Final Pass (Dev 2 verifies, Dev 1 reviews)

```
□ All 6 sections present
□ Action Space table — every field from models.py CacheAction
□ Observation Space table — every field from CacheObservation
□ Reward formulas are the actual math, not descriptions
□ Example Episode code actually runs (test it)
□ No placeholder text
□ Semantic variable names (no x1, y2)
```

#### Step 4.2 🟡 — Clean Git History

```bash
git log --all --oneline                     # review all commits
git grep -l "localhost"                     # must return nothing
git grep -l "torch\|cuda\|tensorflow"       # must return nothing
git status                                  # must be clean
```

#### Step 4.3 🟡 — Final Submission Sequence

Run this exact sequence, in order, **both developers present**:

```bash
# 1. Final build
openenv build                   # exit 0

# 2. Full container smoke test
docker run -d -p 8000:8000 openenv-context_router && sleep 5
curl -X POST http://localhost:8000/reset
curl http://localhost:8000/tasks
curl -X POST http://localhost:8000/grader
curl -X POST http://localhost:8000/baseline
curl http://localhost:8000/health

# 3. Baseline
python baseline/run_baseline.py --base-url http://localhost:8000
# exits 0, 3 scores

# 4. Validate
openenv validate --verbose
# 0 errors

# 5. Deploy final version
openenv push

# 6. Verify live
sleep 30
curl https://<your-space>.hf.space/health
python baseline/run_baseline.py --base-url https://<your-space>.hf.space

# 7. Submit
# Paste HF Space URL into the Scaler hackathon submission form
# DEADLINE: April 7, 2026 — 11:59 PM IST
```

---

## SUMMARY TIMELINE

```
Day 1 (both)     Phase 0    Setup + models.py + schema lock + schema-v1 tag
                 [GATE 0]   schema-v1 tag on main, 0 validate errors

Day 1–3          Phase 1    PARALLEL WORK
  Dev 1                     context_env.py: reset() → step() tasks 1+2+3 → openenv.yaml
  Dev 2                     stub graders → tests → real graders → app.py → baseline → README

Day 3–4 (both)   [MERGE 1]  Integration Merge Ceremony on call
                 [GATE 1]   all tests pass, all endpoints respond, baseline exits 0

Day 4–5 (both)   Phase 2    Docker build → local container test → HF deploy → live verify
                 [GATE 2]   live /health 200, live baseline exits 0

Day 5–6 (both)   Phase 3    Polish, README final pass, clean git, final submission sequence
                             Submit before April 7 11:59 PM IST
```

---

## FILE TREE (Final State)

```
context_router/
├── models.py                        ← 🟡 Both (frozen after Day 1)
├── openenv.yaml                     ← 🟡 Both (synced with models.py always)
├── pyproject.toml                   ← 🟢 Dev 2
├── Dockerfile                       ← 🟢 Dev 2
├── README.md                        ← 🟢 Dev 2
├── server/
│   ├── __init__.py
│   ├── context_env.py               ← 🔵 Dev 1 ONLY
│   └── app.py                       ← 🟢 Dev 2 ONLY
├── graders/
│   ├── __init__.py
│   ├── grader_easy.py               ← 🟢 Dev 2 ONLY
│   ├── grader_medium.py             ← 🟢 Dev 2 ONLY
│   └── grader_hard.py               ← 🟢 Dev 2 ONLY
├── tasks/
│   ├── __init__.py
│   └── task_definitions.py          ← 🟢 Dev 2 (notify Dev 1 of any change)
├── tests/
│   ├── __init__.py
│   ├── test_env_standalone.py       ← 🔵 Dev 1
│   ├── test_grader_easy.py          ← 🟢 Dev 2
│   ├── test_grader_medium.py        ← 🟢 Dev 2
│   └── test_grader_hard.py          ← 🟢 Dev 2
└── baseline/
    └── run_baseline.py              ← 🟢 Dev 2 ONLY
```
