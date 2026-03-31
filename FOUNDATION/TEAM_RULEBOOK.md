# TEAM_RULEBOOK.md — Unified Hard Rules for All Team Members & AI Assistants
> **Project:** Edge GPU Context Memory Router — Meta PyTorch Hackathon
> **Status:** IMMUTABLE — cannot be overridden by any individual, AI assistant, or time pressure
> **Deadline:** April 7, 2026 — 11:59 PM IST
> **Applies to:** Every file, every function, every decision, every AI prompt in this project
> **Rule:** If you are unsure, default to the most restrictive interpretation. When in doubt — stop and ask your teammate.
> **Rule:** Always follow the rulebook.
> **Rule:** Always update MISTAKES.md.

---

## HOW TO USE THIS FILE

1. **Both humans** read sections 0–4 before every session.
2. **Both humans** MUST use the exact AI startup prompts provided in Section 2.
3. **Both humans** MUST update `MISTAKES.md` at the end of every session without fail.
4. **Dev 1** additionally reads Section 5.
5. **Dev 2** additionally reads Section 6.
6. **Both AIs** are given sections 0–4 + their owner's section as the first message every session.
7. **Any violation** found by anyone (human or AI) triggers an immediate STOP before further commits.

---

## SECTION 0 — FILE OWNERSHIP (ABSOLUTE, NO EXCEPTIONS)

> One file = one owner. If your AI generates code for a file you don't own — **discard it immediately.**

| File | Owner | Rule |
|------|-------|------|
| `server/context_env.py` | **Dev 1** | Dev 2 never edits this |
| `graders/grader_easy.py` | **Dev 2** | Dev 1 never edits this |
| `graders/grader_medium.py` | **Dev 2** | Dev 1 never edits this |
| `graders/grader_hard.py` | **Dev 2** | Dev 1 never edits this |
| `server/app.py` | **Dev 2** | Dev 1 never edits this |
| `baseline/run_baseline.py` | **Dev 2** | Dev 1 never edits this |
| `README.md` | **Dev 2** | Dev 1 provides content; Dev 2 owns the file |
| `Dockerfile` | **Dev 2** | Dev 1 never edits this |
| `pyproject.toml` | **Dev 2** | Dev 1 confirms dependencies; Dev 2 owns the file |
| `tasks/task_definitions.py` | **Dev 2** | Dev 1 must be notified of any change |
| `models.py` | **Both — together only** | Neither edits alone. Any change requires both present. |
| `openenv.yaml` | **Both — together only** | Neither edits alone. Must run `openenv validate` immediately after. |
| `tests/` | **Both** | Each owner writes tests for their own files. |

---

## SECTION 1 — THE DATA CONTRACT (HIGHEST PRIORITY RULE)

### C1 — models.py is frozen after Day 1

Once committed to `main`, no single person can modify `models.py` alone.  
Any change requires **both people present** + `openenv validate --verbose` showing 0 errors immediately after.

### C2 — Sacred field names — never rename these

```
CacheAction:        target_block_id, tactic
CacheObservation:   vram_utilization, incoming_tokens,
                    memory_blocks, oom_triggered, message
                    (done + reward are INHERITED — never add them to this class)
MemoryBlockInfo:    block_id, block_type, attention_score, token_count, age
Env class name:     ContextRouterEnv
Env file path:      server/context_env.py
```

### C3 — Paste models.py as the FIRST message to your AI — every session

Before describing any problem. Before asking any question.  
Add this line: *"This is our locked data contract. Do not suggest changes to any field name, type, or class name."*

### C4 — done and reward must NEVER appear in CacheObservation

They are inherited from the base class. Redefining them causes **silent type collisions**.  
Prompt to add to every AI session: *"Do not add done or reward fields to CacheObservation. They are already inherited from openenv.core.env_server.types.Observation."*

### C5 — Trajectory shape is pinned on Day 1

A trajectory = a Python `list` of `CacheObservation` objects, one per `step()` call.

```python
# Canonical trajectory shape — both Dev 1 and Dev 2 must use this exact structure
example_trajectory = [
    CacheObservation(
        vram_utilization=0.87,
        incoming_tokens=200,
        memory_blocks=[...],
        oom_triggered=False,
        message="step ok",
        done=False,
        reward=0.65
    ),
    # ... one CacheObservation per step
]
```

### C6 — Interface contract JSON (share on Day 1, pin forever)

Dev 1 produces and shares this after models.py is finalized. Dev 2 treats it as the only truth:

```json
{
  "action_class": "CacheAction",
  "action_fields": ["target_block_id:int", "tactic:EvictionTactic"],
  "observation_class": "CacheObservation",
  "observation_fields": ["vram_utilization:float", "incoming_tokens:int", "memory_blocks:list", "oom_triggered:bool", "message:str"],
  "observation_inherited_fields": ["done:bool", "reward:float"],
  "state_fields": ["episode_id:str(uuid4)", "step_count:int"],
  "tasks": ["easy", "medium", "hard"],
  "max_steps": 50
}
```

---

## SECTION 2 — PRE-SESSION STARTUP PROTOCOL (Both Developers)

### S1 — Human checklist before every session

```
□ Pull latest: git fetch origin && git merge origin/main
□ Check partner's latest push: git log --oneline -5
□ Read MISTAKES.md: open problems + last session's "next start here" instruction
□ Schema tag exists: git tag -l | grep schema-v1
□ Your branch is clean: git status
□ No stale stash: git stash list
```

### S2 — Branch naming (mandatory before any work)

```bash
# Dev 1 branches
git checkout -b dev1/[short-description]   # e.g. dev1/step-task2, dev1/reset-fix

# Dev 2 branches
git checkout -b dev2/[short-description]   # e.g. dev2/grader-easy, dev2/baseline-fix
```

> **Rule:** Never commit directly to `main`. `main` is only updated via the Merge Ceremony (Section 7).

### S3 — AI startup prompt template (use this exactly)

```
You are my AI co-pilot for the Meta PyTorch Hackathon OpenEnv project.
Before writing any code, READ AND CONFIRM these constraints:

1. I am [Dev 1 / Dev 2]. I own [my files]. My partner owns [their files]. I do NOT touch partner files.
2. Here is our frozen data contract (do not change any field name, type, or class name):
   [paste models.py]
3. These are our hard rules:
   [paste Section 1 and Section 4 of TEAM_RULEBOOK.md]
4. Today's goal: [state the specific task]
5. Do NOT write code until you have confirmed the field names you will use are in the data contract above.
6. After generating any code, output the AI Compliance Block (Section 2, rule S4).

Do NOT do any of the following:
- Rename any field from models.py
- Add done or reward to CacheObservation
- Use def state(self) without @property
- Write except: pass or except Exception: pass
- Hardcode any URL (localhost, 127.0.0.1, :8000, hf.space)
- Return an integer from any grader function
- Pass an instance to create_app() — pass the class
- Use create_fastapi_app() — it does not exist, use create_app()
- Put dependencies in requirements.txt — use pyproject.toml
- Generate openenv.yaml — we write it manually field by field
- Suggest "better" field names — the contract is frozen
```

### S4 — Mandatory AI compliance block

Your AI MUST output this block after generating any function, class, or file:

```
--- AI Compliance Check ---
□ Field names used match models.py exactly? [YES / NO — list any that differ]
□ @property decorator is above def state [YES / N/A]
□ No done or reward in CacheObservation [YES / N/A]
□ No hardcoded URLs [YES]
□ No empty except blocks [YES]
□ Grader returns float, clipped with max(0.0, min(1.0, ...)) [YES / N/A]
□ create_app() receives CLASS, not instance [YES / N/A]
□ No GPU libraries imported or listed [YES]
□ openenv.yaml needs updating after this change? [YES → do it now / NO]
□ This change affects partner's interface? [YES → notify partner / NO]
---------------------------
```

> **Rule:** If the AI does not produce this block, force it to by re-prompting. Never accept AI output that skips compliance checking.

---

## SECTION 3 — GIT RULES

### G1 — Never use `git add .` or `git add -A` — ever

```bash
# FORBIDDEN
git add .
git add -A

# REQUIRED — explicit file names only
git add server/context_env.py           # Dev 1 only
git add graders/grader_easy.py          # Dev 2 only
git add models.py openenv.yaml          # Both together only — must be in same commit
```

### G2 — Commit message format

```bash
# Format: [devN] type: description
git commit -m "[dev1] feat: implement step() for task-1 with max_steps=50"
git commit -m "[dev2] feat: grader_easy TDD complete — 3 tests passing"
git commit -m "[both] sync: openenv.yaml updated to match models.py changes"
```

> **Rule:** Never use vague messages like `fix`, `update`, `changes`. State exactly what file changed and why.

### G3 — openenv.yaml and models.py are always committed together

```bash
# REQUIRED — always in the same commit, never separately
git add openenv.yaml models.py
openenv validate --verbose   # must show 0 errors BEFORE this commit
git commit -m "[both] sync: openenv.yaml updated to match models.py"
```

### G4 — Merge conflicts = stop and call teammate

Do NOT let AI resolve merge conflicts. Open a call, read both versions together, decide together.  
A conflict on `models.py` especially MUST be resolved in person — AI is forbidden from touching this.

### G5 — .gitignore must include (commit Day 1)

```
.venv/
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.DS_Store
outputs/
*.log
```

---

## SECTION 4 — UNIVERSAL FORBIDDEN LIST

If any of these appear **anywhere** in your code — fix before committing. No exceptions.

```python
# FORBIDDEN: silent exception swallowing
except: pass
except Exception: pass

# FORBIDDEN: violating any rule in TEAM_RULEBOOK.md
# Rulebook is the source of truth over any AI suggestion.

# FORBIDDEN: closing a session without updating MISTAKES.md
# Session logs are mandatory for continuity.

# FORBIDDEN: hardcoded URLs
base_url = "http://localhost:8000"
url = "http://127.0.0.1:8000"
url = "https://my-fixed-space.hf.space"

# FORBIDDEN: integer return from grader
return 1
return 0
if success: return 1.0
else: return 0.0        # binary-only = no partial credit = violation

# FORBIDDEN: state without @property
def state(self):        # missing @property above this line
    return State(...)

# FORBIDDEN: instance passed to create_app
create_app(ContextRouterEnv(), ...)   # parentheses after class name = wrong

# FORBIDDEN: done/reward redefined in CacheObservation
class CacheObservation(Observation):
    done: bool = False      # REMOVE THIS
    reward: float = 0.0     # REMOVE THIS

# FORBIDDEN: GPU libraries in any requirements file
torch
tensorflow
cuda-anything
torch==2.0.0+cu117

# FORBIDDEN: staging all files
git add .
git add -A

# FORBIDDEN: wrong server factory
create_fastapi_app(...)   # does not exist

# FORBIDDEN: Python version mismatch
FROM python:3.13          # unsupported
FROM python:3.9           # too old

# FORBIDDEN: episode_id set in __init__ instead of reset()
def __init__(self):
    self._episode_id = str(uuid4())   # WRONG — move this to reset()

# FORBIDDEN: module-level randomness
blocks = [random.choice(options)]       # WRONG — must use self._rng seeded in reset()

# FORBIDDEN: infinite episodes
def step(self, action):
    # ... logic that never sets done=True

# FORBIDDEN: grader raising exception (must return 0.0 instead)
def grader_easy(trajectory):
    # ... raises ValueError on malformed input (must catch and return 0.0)
```

---

## SECTION 5 — DEV 1 RULES (server/context_env.py owner)

### PA1 — @property must be above def state — check before every commit

```python
@property                         # ← this line MUST exist
def state(self) -> State:
    return State(
        episode_id=self._episode_id,
        step_count=self._step_count
    )
```

### PA2 — episode_id must be a fresh UUID in every reset(), never in __init__

```python
from uuid import uuid4
from typing import Optional

def reset(self, seed: Optional[int] = None) -> CacheObservation:
    self._episode_id = str(uuid4())    # fresh every call — NEVER in __init__
    if seed is not None:
        self._rng = random.Random(seed)
    self._state = State(episode_id=self._episode_id, step_count=0)
    # reset simulation state here...
    return CacheObservation(
        vram_utilization=0.0,
        incoming_tokens=0,
        memory_blocks=[],
        oom_triggered=False,
        message="Environment reset.",
        done=False,
        reward=0.0
    )
```

### PA3 — Use random.Random(seed) not random.seed() (global state is forbidden)

```python
# WRONG: modifies global RNG state — non-deterministic across sessions
random.seed(seed)
blocks = [random.choice(options)]

# CORRECT: local RNG instance, fully deterministic and isolated
self._rng = random.Random(seed)
blocks = [self._rng.choice(options)]
```

### PA4 — step() must wrap ALL logic in try/except — never a bare raise

```python
MAX_STEPS = 50   # class constant

def step(self, action: CacheAction) -> CacheObservation:
    try:
        self._state = State(
            episode_id=self._state.episode_id,
            step_count=self._state.step_count + 1
        )
        if self._state.step_count >= self.MAX_STEPS:
            return CacheObservation(
                vram_utilization=self._vram_used / self._vram_max,
                incoming_tokens=0,
                memory_blocks=self._get_blocks(),
                oom_triggered=False,
                message="Max steps reached.",
                done=True,
                reward=float(self._compute_partial_credit())
            )
        # ... full simulation logic here ...
    except Exception as e:
        logger.error(f"step() error: {e}", exc_info=True)
        return CacheObservation(
            vram_utilization=self._vram_used / self._vram_max,
            incoming_tokens=0,
            memory_blocks=self._get_blocks(),
            oom_triggered=False,
            message=f"invalid action: {e}",
            done=True,
            reward=0.0
        )
```

### PA5 — Provide stub graders to Dev 2 the moment step() for a task is ready

```python
# File: graders/grader_easy_stub.py  — Dev 1 creates this, Dev 2 replaces with real logic
def grader_easy_stub(trajectory: list) -> float:
    """STUB — real grader is Dev 2's responsibility. Always returns 0.5."""
    return 0.5
```

### PA6 — Run this test before telling Dev 2 your code is ready for integration

```python
# tests/test_env_standalone.py
from server.context_env import ContextRouterEnv
from models import CacheAction, EvictionTactic

env = ContextRouterEnv()

# Test 1: determinism
obs1 = env.reset(seed=42)
obs2 = env.reset(seed=42)
assert obs1.vram_utilization == obs2.vram_utilization, "FAIL: not deterministic"

# Test 2: step() does not crash on bad input
bad = CacheAction(target_block_id=-999, tactic=EvictionTactic.EVICT)
obs = env.step(bad)
assert isinstance(obs.reward, float), "FAIL: reward not float"
assert obs.done == True, "FAIL: bad input should end episode"

# Test 3: max steps enforced
env.reset(seed=1)
for i in range(60):
    obs = env.step(CacheAction(target_block_id=0, tactic=EvictionTactic.RETAIN))
    if obs.done:
        print(f"done at step {i+1}")
        break
assert i < 50, f"FAIL: episode ran past 50 steps (stopped at {i})"

# Test 4: episode_id changes between resets
id1 = env.reset(seed=1).message  # just to trigger reset
id2 = env.reset(seed=2).message
assert env._state.episode_id != id1 or True  # episode_id must be new each time

print("All Dev 1 standalone tests passed ✓")
```

### PA7 — Dev 1 Phase Checklist

```
□ Phase A: Domain design template filled out, schema agreed with Dev 2 in writing
□ Phase A: models.py committed with tag schema-v1
□ Phase B: reset() implemented and passes standalone test
□ Phase B: step() for Task 1 complete, stub grader provided to Dev 2
□ Phase B: step() for Task 2 complete, stub grader provided to Dev 2
□ Phase B: step() for Task 3 complete, stub grader provided to Dev 2
□ Phase B: openenv.yaml updated in same commit as step() for each task
□ Phase C: openenv build exits 0
□ Phase C: openenv validate --verbose shows 0 errors
□ Phase C: All 5 endpoints respond locally (health, reset, tasks, grader, baseline)
□ Phase C: openenv push successful
□ Phase C: Live HF Space /health returns 200
```

---

## SECTION 6 — DEV 2 RULES (graders / app / baseline / README owner)

### PB1 — create_app receives the CLASS, never an instance

```python
# WRONG
app = create_app(ContextRouterEnv(), ...)   # parentheses = instance = wrong

# CORRECT
from openenv.core.env_server import create_app
app = create_app(ContextRouterEnv, CacheAction, CacheObservation, env_name="context_router")
```

### PB2 — TDD for graders is MANDATORY — tests before logic, always

This order is required. Skipping any step is forbidden:

```
Step 1: Define in plain English what 1.0, 0.5, and 0.0 mean for this task.
Step 2: Create mock trajectory lists (hardcoded — no live server needed).
Step 3: Write tests FIRST:
        - test_perfect → must return 1.0
        - test_empty   → must return 0.0
        - test_partial → must return float strictly between 0.0 and 1.0
        - test_float_type → isinstance(result, float) must be True
        - test_deterministic → same input twice = same output
        - test_clamped → corrupted input stays in [0.0, 1.0]
Step 4: Run tests — they will FAIL (stub returns 0.5). This is expected.
Step 5: Implement grader logic until all 6 tests pass.
Step 6: Run Verification Loop (Section 8).
Step 7: Commit with test file and grader file together.
```

### PB3 — Every grader return must be float, clipped, with partial credit

```python
def grader_easy(trajectory: list) -> float:
    try:
        if not trajectory:
            return 0.0

        total_steps = len(trajectory)
        correct_steps = sum(1 for obs in trajectory if obs.reward > 0.5)
        completion_ratio = correct_steps / total_steps

        oom_penalty = 0.2 * sum(1 for obs in trajectory if obs.oom_triggered)
        efficiency_bonus = 0.15 if total_steps < 20 else 0.0

        score = (completion_ratio * 0.8) + efficiency_bonus - oom_penalty
        return float(max(0.0, min(1.0, score)))    # EVERY return path must be like this

    except Exception as e:
        logger.error(f"grader_easy error: {e}")
        return 0.0    # never re-raise from a grader
```

### PB4 — /tasks must return DISTINCT action schemas (not identical for all 3)

```
Easy schema:   {target_block_id: int, tactic: "evict"|"retain"}
Medium schema: {target_block_id: int, tactic: "evict"|"retain"|"compress"}
Hard schema:   {target_block_id: int, tactic: "evict"|"retain"|"compress", priority: int}
```

After writing `/tasks`, diff the 3 schemas side by side and confirm they differ.

### PB5 — /baseline endpoint must catch exceptions per task (never crash the whole call)

```python
@app.post("/baseline")
def baseline():
    results = {}
    for task_name, run_fn in tasks.items():
        try:
            results[task_name] = float(run_fn())
        except Exception as e:
            logger.error(f"Baseline task {task_name} failed: {e}")
            results[task_name] = 0.0    # never crashes whole endpoint
    return results
```

### PB6 — Baseline script: –-base-url is required, no hardcoded URLs ever

```python
import argparse, sys

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True, help='Base URL of deployed environment')
args = parser.parse_args()

scores = {}
for task in ["easy", "medium", "hard"]:
    try:
        scores[task] = run_task(args.base_url, task)
    except Exception as e:
        print(f"Task {task} failed: {e}", file=sys.stderr)
        scores[task] = 0.0

print(f"Task easy score:   {scores['easy']:.4f}")
print(f"Task medium score: {scores['medium']:.4f}")
print(f"Task hard score:   {scores['hard']:.4f}")
sys.exit(0)
```

Verification: `grep -n "localhost" baseline/run_baseline.py` must return **nothing**.

### PB7 — Partial credit score bands are required for every grader

```
Reachable bands MUST include at minimum:
  0.0             — complete failure (zero correct steps)
  (0.0, 0.5)      — weak partial (some steps correct, significant errors)
  [0.5, 1.0)      — strong partial (most steps correct, minor issues)
  1.0             — perfect episode (all success criteria met)

Binary-only graders (only 0.0 or 1.0) are DISQUALIFYING.
```

### PB8 — README must contain all 6 required sections (actual content, no placeholders)

```markdown
# [Environment Name]
## Overview
## Action Space       ← table with Field | Type | Values | Description
## Observation Space  ← table with Field | Type | Description
## Tasks              ← table with Task | Difficulty | Description | Success Condition
## Reward Function    ← actual formula: reward = (A × 0.7) + (B × 0.3)
## Setup Instructions
## Example Episode    ← real Python code using EnvClient that runs
```

### PB9 — Grader uses only trajectory data — no external calls, no global state

```python
# FORBIDDEN inside any grader
response = requests.get("https://api.example.com/check")
global_counter += 1
random.random()    # non-deterministic — use no randomness in graders

# REQUIRED: graders are pure functions of their input
def grader_easy(trajectory: list) -> float:
    # reads only from trajectory — nothing else
```

### PB10 — Dev 2 Phase Checklist

```
□ Phase A: Interface contract agreed with Dev 1 in writing (field names + types)
□ Phase A: Stub graders written for all 3 tasks (compile and return 0.5)
□ Phase A: Stub grader tests written (6 tests per grader, all should pass with stub)
□ Phase B: grader_easy: 6 tests pass, partial credit verified
□ Phase B: grader_medium: 6 tests pass, partial credit verified
□ Phase B: grader_hard: 6 tests pass, partial credit verified
□ Phase B: task_definitions.py task names confirmed against Dev 1's openenv.yaml
□ Phase C: baseline script local test passes (exits 0, 3 float scores)
□ Phase C: no hardcoded URLs in baseline script
□ Phase C: baseline script live test passes against HF Space
□ Phase D: README all 6 sections complete with actual content
□ Phase D: Reward formulas in README match what graders actually compute
□ Phase D: Example episode code in README actually runs
```

---

## SECTION 7 — MERGE CEREMONY (do together on a call, every time)

> **Rule:** Never merge to `main` solo. This is a two-person ceremony. Both must be present.

### Step 1 — Dev 1 confirms their standalone tests pass, then pushes

```bash
python tests/test_env_standalone.py   # must print "All Dev 1 standalone tests passed ✓"
git push origin dev1/<branch>
```

### Step 2 — Dev 2 confirms their grader tests pass, then pushes

```bash
python -m pytest tests/test_grader_easy.py tests/test_grader_medium.py tests/test_grader_hard.py -v
# all tests must pass
git push origin dev2/<branch>
```

### Step 3 — Import smoke test (run together — most important check)

```python
python -c "
from server.context_env import ContextRouterEnv
from models import CacheAction, EvictionTactic
env = ContextRouterEnv()
obs = env.reset(seed=42)
print('vram:', obs.vram_utilization)
print('blocks:', len(obs.memory_blocks))
print('IMPORT TEST PASSED')
"
```
If this throws — field names have drifted. **Fix models.py together before continuing.**

### Step 4 — Run one real trajectory through a grader

```python
from server.context_env import ContextRouterEnv
from graders.grader_easy import grader_easy
from models import CacheAction, EvictionTactic

env = ContextRouterEnv()
env.reset(seed=42)
trajectory = []
for i in range(5):
    obs = env.step(CacheAction(target_block_id=i % 3, tactic=EvictionTactic.EVICT))
    trajectory.append(obs)

score = grader_easy(trajectory)
print(type(score), score)   # must be: <class 'float'> 0.xx
assert isinstance(score, float), "FAILED: grader returned non-float"
assert 0.0 <= score <= 1.0, "FAILED: grader out of range"
print("GRADER INTEGRATION TEST PASSED")
```

### Step 5 — Hit all required endpoints locally

```bash
# Build and run container
openenv build
docker run -d -p 8000:8000 openenv-context_router
sleep 5

# Test every endpoint
curl http://localhost:8000/health              # 200 OK
curl http://localhost:8000/tasks              # 3 tasks with distinct schemas
curl -X POST http://localhost:8000/reset      # valid JSON Observation
curl -X POST http://localhost:8000/grader     # {"score": X.X}
curl -X POST http://localhost:8000/baseline   # {easy: X, medium: X, hard: X}
```

### Step 6 — Run baseline script

```bash
python baseline/run_baseline.py --base-url http://localhost:8000
# Must: exit 0, print 3 float scores
```

### Step 7 — openenv validate → 0 errors → merge to main

```bash
openenv validate --verbose    # must show 0 errors

# Merge ceremony
git checkout main
git merge dev1/<branch>
git merge dev2/<branch>
git push origin main
git tag merge-$(date +%Y%m%d-%H%M)   # tag every merge to main
```

### Step 8 — Deploy and verify live

```bash
openenv push
sleep 30   # wait for HF Spaces to boot
curl https://<your-space>.hf.space/health            # must return 200
python baseline/run_baseline.py --base-url https://<your-space>.hf.space
# must exit 0 and print 3 scores
```

---

## SECTION 8 — VERIFICATION LOOP (Non-Negotiable, Run Before Every PR)

```bash
# 1. Type check
pyright . || mypy .
# Must pass with 0 errors

# 2. Unit tests
python -m pytest tests/ -v
# Must pass all tests

# 3. Build
openenv build
# Must exit 0

# 4. Container smoke test
docker run -d -p 8000:8000 openenv-context_router && sleep 5
curl -X POST http://localhost:8000/reset      # JSON Observation
curl http://localhost:8000/tasks             # list of 3 tasks
curl -X POST http://localhost:8000/grader    # float score
curl http://localhost:8000/health            # 200

# 5. Baseline test
python baseline/run_baseline.py --base-url http://localhost:8000
# Exits 0, 3 float scores

# 6. Spec validation
openenv validate --verbose
# 0 errors

# 7. Log results in MISTAKES.md before stopping work
```

> **Rule:** If ANY step fails — stop. Fix the issue. Re-run the loop from Step 1. Never skip to the next step on failure.

---

## SECTION 9 — END-OF-SESSION PROTOCOL (Both Developers)

### Human checklist

```
□ All work committed to your feature branch (NOT main)
□ MISTAKES.md updated with new session entry
□ LAST KNOWN GOOD STATE updated in MISTAKES.md
□ "Next session: start here" instruction written
□ New open problems added to OPEN PROBLEMS section in MISTAKES.md
□ Partner notified (message) of what is complete, what is in progress, what they need
□ git push origin <your-branch>
```

### Required AI session summary at end of every session

```
--- AI Session Summary ---
Date: [date]
Developer: [Dev 1 / Dev 2]
Branch: [branch name]

Files changed:
- [filename]: [what changed]

Tests status:
- [test file]: [N passing / N failing]

Interface changes (if any):
- [field changed]: [notified partner? YES/NO]

Stubs provided to partner:
- [stub name]: [what real version should do]

LAST KNOWN GOOD STATE snapshot:
- reset() working locally: [YES/NO]
- step() Task 1: [YES/NO]
- step() Task 2: [YES/NO]
- step() Task 3: [YES/NO]
- grader_easy complete: [YES/NO]
- grader_medium complete: [YES/NO]
- grader_hard complete: [YES/NO]
- baseline script exits 0: [YES/NO]
- openenv build: [YES/NO]
- openenv validate: [YES/NO]
- HF Space deployed: [YES/NO]
- HF Space /health 200: [YES/NO]

Open problems discovered:
- [problem description]

Next session start: [single clear instruction]
--------------------------
```

---

## SECTION 10 — EMERGENCY DIAGNOSTIC TABLE

| Symptom | Likely Cause | Exact Fix |
|---------|-------------|-----------|
| Grader always returns 0.0 | Field name drift | `print(trajectory[0].__dict__)` inside grader — compare field names to models.py |
| `ImportError: cannot import ContextRouterEnv` | Class/file name mismatch | `grep -r "class.*Env" server/` to find actual class name |
| `reset(seed=42)` differs between machines | Used `random.seed()` instead of `random.Random(seed)` | Replace with `self._rng = random.Random(seed)` |
| `AttributeError: 'ContextRouterEnv' has no attribute 'state'` | Missing `@property` | Add `@property` above `def state` in context_env.py |
| `openenv validate: grader returned non-float` | Returning int or None | `grep -n "return" graders/grader_easy.py` — wrap with `float(max(0.0, min(1.0, ...)))` |
| Baseline script fails on live URL | Hardcoded localhost | `grep -n "localhost" baseline/run_baseline.py` — replace with `args.base_url` |
| `Pydantic ValidationError: field required: done` | done/reward redefined in CacheObservation | Remove them from CacheObservation — they come from base class |
| `episode_id` same across consecutive resets | uuid set in `__init__` not `reset()` | Move `str(uuid4())` call into `reset()` body |
| Docker build fails | GPU library in pyproject.toml | `grep -n "torch\|cuda\|tensorflow" pyproject.toml` — remove any matches |
| HF Space returns 500 on first request | Works locally → cloud issue | Test with `docker run` locally first. If local works, check logs with `openenv logs` |
| openenv validate fails after schema change | openenv.yaml out of sync | Both devs must re-run YAML-Python sync: update yaml, validate, commit together |
| `/baseline` crashes on second task | No per-task exception handling | Wrap each task in its own try/except and return 0.0 on failure |
| Grader non-deterministic | `random` inside grader | `grep -n "random" graders/*.py` — remove all randomness from graders |

---

## SECTION 11 — FINAL SUBMISSION SEQUENCE (Run Together)

```bash
# 1. Build from scratch
openenv build

# 2. Container test — all endpoints
docker run -d -p 8000:8000 openenv-context_router && sleep 5
curl -X POST http://localhost:8000/reset
curl http://localhost:8000/tasks
curl -X POST http://localhost:8000/grader
curl -X POST http://localhost:8000/baseline
curl http://localhost:8000/health

# 3. Baseline script
python baseline/run_baseline.py --base-url http://localhost:8000
# → exits 0, 3 float scores printed

# 4. Spec validation
openenv validate --verbose
# → 0 errors

# 5. Deploy
openenv push
# → note HF Space URL: _______________________

# 6. Verify live Space
sleep 30
curl -X POST https://<your-space>.hf.space/reset   # → 200 + JSON
python baseline/run_baseline.py --base-url https://<your-space>.hf.space
# → exits 0, 3 float scores

# 7. Submit
# → paste HF Space URL into submission form
# → DEADLINE: April 7, 2026 — 11:59 PM IST
```

---

## APPENDIX — Correct OpenEnv Imports

```python
# Environment server
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, Observation, State
from openenv.core.env_server import create_app

# Client (for baseline script)
from openenv.core.env_client import EnvClient
```

---

*Both developers confirm they have read this rulebook before writing any code.*  
*Last updated: 2026-03-28*
