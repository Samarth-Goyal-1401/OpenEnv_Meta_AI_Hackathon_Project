# OpenEnv Complete Guide — Everything You Need to Know

> **Purpose:** A single document to learn OpenEnv from zero to submission-ready.
> **Audience:** Beginners to OpenEnv / RL environments.
> **Reading time:** ~30 min for concepts, ~2 hrs with code walkthroughs.
> **Last Updated:** 2026-03-26

---

## TABLE OF CONTENTS

1. [The Big Picture — What Are We Building?](#1-the-big-picture)
2. [Core Concepts — RL Environments Explained](#2-core-concepts)
3. [OpenEnv Architecture — How It All Fits Together](#3-architecture)
4. [The 3 APIs — step(), reset(), state](#4-the-3-apis)
5. [Project File-by-File Walkthrough](#5-file-walkthrough)
6. [Data Flow — A Complete Episode](#6-data-flow)
7. [Graders & Reward Functions](#7-graders)
8. [Deployment Pipeline](#8-deployment)
9. [Common Pitfalls & How to Avoid Them](#9-pitfalls)
10. [Quick Reference Cheat Sheet](#10-cheat-sheet)

---

## 1. The Big Picture — What Are We Building? {#1-the-big-picture}

### You're Building a GYM, Not a Bodybuilder

Imagine you're building a gym where AI agents come to train. You don't train the agent yourself — you build the **equipment** (environment), the **rules** (tasks), and the **scorecard** (graders). The agents show up, work out, and get scored.

```
                    YOU BUILD THIS
                    ┌──────────────────────────────┐
                    │   RL Environment (OpenEnv)   │
                    │                              │
   AI Agent ──────► │  reset() → initial state     │
   (not you)        │  step(action) → observation  │
                    │  state → metadata            │
                    │  grader → score 0.0-1.0      │
                    └──────────────────────────────┘
```

### What Exactly Is an OpenEnv Environment?

It's a **Docker container** running a **FastAPI server** that exposes a standardized API for AI agents to interact with. The server simulates some real-world scenario (medical diagnosis, supply chain, code review, etc.) and the agent learns by trial and error.

### The Hackathon Requirement in One Sentence

> Build a real-world RL environment with 3 difficulty levels, deploy it to HuggingFace Spaces, and make sure it passes all automated validation checks.

---

## 2. Core Concepts — RL Environments Explained {#2-core-concepts}

### The Episode Loop

Every interaction happens in **episodes**. An episode is like one "game" or "attempt":

```
┌──────────────────────────────────────────────────────────────┐
│                        ONE EPISODE                           │
│                                                              │
│   reset() ──► step(a₁) ──► step(a₂) ──► ... ──► step(aₙ)   │
│      │           │            │                     │        │
│      ▼           ▼            ▼                     ▼        │
│   obs₀        obs₁         obs₂                  obsₙ       │
│  (initial)   (+ reward)   (+ reward)          (done=True)    │
│                                                              │
│   After done=True → Grader scores the episode: 0.0 to 1.0   │
└──────────────────────────────────────────────────────────────┘
```

### The Three Core Concepts

| Concept | What It Is | Real-World Analogy |
|---------|-----------|-------------------|
| **Action** | What the agent *does* each step | Doctor choosing a test to run |
| **Observation** | What the agent *sees* after each step | Test results coming back |
| **State** | Internal metadata about the episode | Patient chart behind the scenes |

### Rewards vs Grader Scores

- **Reward** (per-step): Given after every `step()`. Guides real-time learning. Can be any float.
- **Grader Score** (per-episode): Given after the episode ends. Evaluates overall performance. Must be `float` in `[0.0, 1.0]`.

Think of reward like a coach saying "good move" or "bad move" during the game, and the grader score like the final
exam result.

---

## 3. OpenEnv Architecture — How It All Fits Together {#3-architecture}

### The Full Stack

```
┌────────────────────────────────────────────────────────────────────┐
│                      1. TRAINING LOOP / AGENT                      │
│   (An RL algorithm or LLM that learns by interacting)              │
│   Uses: EnvClient (WebSocket to connect to server)                 │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │
                            WebSocket (/ws)
                    Persistent connection, ~0.1ms per frame
                                   │
┌──────────────────────────────────▼─────────────────────────────────┐
│                   2. FASTAPI SERVER (inside Docker)                 │
│                                                                    │
│   create_app(EnvironmentClass, ActionType, ObservationType)        │
│                                                                    │
│   Each WebSocket connection → own Environment instance             │
│                                                                    │
│   Built-in endpoints:   /ws, /reset, /step, /state, /health       │
│   Custom endpoints:     /tasks, /grader, /baseline                 │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │
                            Python calls
                                   │
┌──────────────────────────────────▼─────────────────────────────────┐
│                   3. YOUR ENVIRONMENT CLASS                         │
│                                                                    │
│   class MyEnvironment(Environment):                                │
│       def reset(self) -> MyObservation       # start new episode   │
│       def step(self, action) -> MyObservation # process action     │
│       @property                                                    │
│       def state(self) -> State               # return metadata     │
│                                                                    │
│   This is where YOUR domain logic lives                            │
│   (medical sim, supply chain, code review, etc.)                   │
└────────────────────────────────────────────────────────────────────┘
```

### Why WebSocket?

OpenEnv uses WebSocket instead of REST/HTTP for the primary communication:
- **Persistent connection**: No TCP handshake per request (~0.1ms vs ~10-50ms)
- **Isolated sessions**: Each WebSocket connection gets its own Environment instance
- **Stateful**: The connection maintains state across multiple step() calls
- HTTP endpoints also exist (`/reset`, `/step`, `/state`) but WebSocket is canonical

---

## 4. The 3 APIs — step(), reset(), state {#4-the-3-apis}

### reset() — Start a New Episode

```python
def reset(self, seed: Optional[int] = None) -> MyObservation:
    """
    Called ONCE at the start of every episode.
    
    What it does:
    1. Generates a fresh episode_id (UUID)
    2. Resets all internal state to initial conditions
    3. If seed is provided, seeds all randomness for reproducibility
    4. Returns the initial observation (what the agent "sees" first)
    
    RULES:
    - MUST never raise an exception
    - MUST be callable at ANY time (even mid-episode)
    - MUST generate fresh episode_id every time
    - State from previous episodes MUST NOT carry over
    """
    if seed is not None:
        self._rng = random.Random(seed)
    
    self._state = State(episode_id=str(uuid4()), step_count=0)
    
    # Return initial observation — what the agent sees first
    return MyObservation(
        result="Environment initialized. Ready for first action.",
        success=True,
        done=False,      # Episode just started, not done yet
        reward=0.0       # No reward on reset
    )
```

### step(action) — Process One Agent Action

```python
def step(self, action: MyAction) -> MyObservation:
    """
    Called EVERY TURN after reset().
    
    What it does:
    1. Validates the incoming action
    2. Executes the domain logic (your custom simulation)
    3. Updates internal state
    4. Checks if episode should end (done=True)
    5. Calculates reward for this step
    6. Returns observation with reward + done flag
    
    RULES:
    - MUST NEVER raise an unhandled exception (wrap in try/except)
    - MUST eventually return done=True (no infinite episodes)
    - MUST handle malformed input gracefully
    - MUST return valid Observation even for bad input
    """
    try:
        self._state.step_count += 1
        
        # === YOUR DOMAIN LOGIC HERE ===
        result = self._process_action(action)
        is_done = self._check_completion()
        reward = self._calculate_reward(result)
        
        return MyObservation(
            result=result,
            success=True,
            done=is_done,
            reward=reward
        )
    except Exception as e:
        # DEFENSIVE: Never crash — return error observation
        return MyObservation(
            result=f"Error: {str(e)}",
            success=False,
            done=True,      # End episode on error
            reward=0.0       # No reward for errors
        )
```

### state (property) — Get Episode Metadata

```python
@property  # NOTE: This is a PROPERTY, not a method!
def state(self) -> State:
    """
    Returns current episode metadata.
    
    The State class is provided by OpenEnv core:
    - episode_id: str (UUID)
    - step_count: int
    
    RULES:
    - MUST be a @property, not a method
    - episode_id MUST be a UUID string
    """
    return self._state
```

### How They Work Together (Timeline)

```
Agent                           Environment
  │                                 │
  │──── reset() ────────────────────│
  │                                 │ Creates new episode_id
  │                                 │ Initializes state
  │◄─── Observation(done=False) ────│
  │                                 │
  │──── step(action_1) ────────────│
  │                                 │ Processes action
  │                                 │ Calculates reward
  │◄─── Observation(reward=0.3) ───│
  │                                 │
  │──── step(action_2) ────────────│
  │                                 │ Processes action
  │◄─── Observation(reward=0.5) ───│
  │                                 │
  │──── step(action_3) ────────────│
  │                                 │ Processes action
  │                                 │ Detects completion
  │◄─── Observation(done=True) ────│
  │                                 │
  │──── [Episode ends] ────────────│
  │──── grader(trajectory) ────────│
  │◄─── score: 0.73 ──────────────│
```

---

## 5. Project File-by-File Walkthrough {#5-file-walkthrough}

When you run `openenv init my_env`, it creates this structure. Here's what every file does:

### 📁 Root Level

#### `openenv.yaml` — The Manifest (MANDATORY)
```yaml
# This is like a package.json for your environment
# OpenEnv reads this to understand your environment

name: my_env
version: "0.1.0"
description: "A description of what your environment does"
schema_version: "1.0"

# Lists all tasks the environment supports
tasks:
  - name: easy_task
    difficulty: easy
    description: "Simple version of the task"
  - name: medium_task
    difficulty: medium
    description: "Intermediate challenge"
  - name: hard_task
    difficulty: hard
    description: "Expert-level challenge"

# Documents the action and observation formats
action_schema:
  type: object
  properties:
    command:
      type: string
      description: "The action to take"

observation_schema:
  type: object
  properties:
    result:
      type: string
      description: "What happened"
```

**Why it matters:** `openenv validate` checks this file against your actual code. If it's wrong or missing, you're auto-disqualified.

---

#### `pyproject.toml` — Dependencies
```toml
[project]
name = "my_env"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "openenv-core",
    "fastapi",
    "uvicorn",
    "pydantic",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Why it matters:** This is the PRIMARY dependency file. The Dockerfile uses `uv sync` to install from this. NOT `requirements.txt`.

---

#### `__init__.py` — Package Exports
```python
# Makes the environment importable as a package
from .models import MyAction, MyObservation
from .client import MyEnv

__all__ = ["MyAction", "MyObservation", "MyEnv"]
```

**Why it matters:** When users `pip install` your environment, this is what they can import.

---

### 📁 models.py — Data Types (THE FOUNDATION)

This is the **first file you should write**. Everything else depends on it.

```python
"""
models.py — Define the data contracts for your environment.

These are Pydantic models that ensure type safety.
They define WHAT the agent can do and WHAT it sees.
"""
from pydantic import Field
from openenv.core.env_server.types import Action, Observation

# ──────────────────────────────────────────────
# ACTION — What the agent SENDS each step
# ──────────────────────────────────────────────
class MyAction(Action):
    """
    Represents one action the agent can take.
    
    RULES:
    - MUST subclass openenv.core.env_server.types.Action
    - MUST use typed Pydantic fields (not free-text strings)
    - Each task SHOULD have slightly different action fields
    """
    command: str = Field(
        ...,
        description="The command to execute",
        examples=["diagnose", "order_test", "prescribe"]
    )
    parameters: dict = Field(
        default_factory=dict,
        description="Command-specific parameters"
    )


# ──────────────────────────────────────────────
# OBSERVATION — What the agent RECEIVES after each step
# ──────────────────────────────────────────────
class MyObservation(Observation):
    """
    Represents what the agent sees after taking an action.
    
    IMPORTANT: The Observation base class already provides:
    - done: bool     → whether episode is finished
    - reward: float  → reward for this step
    
    DO NOT redefine done or reward — they're inherited!
    """
    result: str = Field(
        ...,
        description="Description of what happened"
    )
    success: bool = Field(
        ...,
        description="Whether the action was valid and processed"
    )
    # Optional: Add more fields specific to your domain
    # score_so_far: float = Field(0.0, description="Running score")
    # available_actions: list = Field(default_factory=list)
```

**Key insight:** The `Observation` base class already has `done` and `reward` fields built in. You don't need (and MUST NOT) redefine them. Just set them when you return an observation.

---

### 📁 server/my_environment.py — Your Core Logic (THE BRAIN)

This is where your domain simulation lives.

```python
"""
server/my_environment.py — The heart of your environment.

This class implements the RL environment logic:
- What happens when an episode starts (reset)
- What happens when the agent takes an action (step)
- What the current state looks like (state property)
"""
import random
from uuid import uuid4
from typing import Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from models import MyAction, MyObservation


class MyEnvironment(Environment):
    """
    Your custom RL environment.
    
    ARCHITECTURE NOTE:
    The server creates ONE instance per WebSocket connection.
    This means each agent session is completely isolated.
    You don't need to worry about concurrent access.
    """
    
    def __init__(self):
        """Initialize with a fresh state."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._rng = random.Random()
        # Your domain-specific state:
        self._domain_data = {}
        self._max_steps = 50  # Safety limit — prevents infinite episodes
    
    def reset(self, seed: Optional[int] = None) -> MyObservation:
        """
        Start a new episode.
        
        This is called:
        - At the very beginning
        - Between episodes
        - Sometimes mid-episode (agent gives up and restarts)
        
        MUST:
        - Generate fresh episode_id
        - Clear all previous state
        - Seed randomness if seed is provided
        - Return initial observation
        - NEVER raise an exception
        """
        if seed is not None:
            self._rng = random.Random(seed)
        
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._domain_data = self._initialize_scenario()
        
        return MyObservation(
            result="New episode started. Here's what you need to do: ...",
            success=True,
            done=False,
            reward=0.0
        )
    
    def step(self, action: MyAction) -> MyObservation:
        """
        Process one agent action and return the result.
        
        This is the MOST IMPORTANT method. It's called every turn.
        
        MUST:
        - Never raise unhandled exceptions (wrap in try/except)
        - Eventually return done=True
        - Handle malformed input gracefully
        - Return meaningful reward (not just 0/1)
        """
        try:
            self._state.step_count += 1
            
            # Safety: Force episode end if too many steps
            if self._state.step_count >= self._max_steps:
                return MyObservation(
                    result="Maximum steps reached. Episode ended.",
                    success=False,
                    done=True,
                    reward=0.0
                )
            
            # === YOUR DOMAIN LOGIC ===
            result, reward, is_done = self._execute_action(action)
            
            return MyObservation(
                result=result,
                success=True,
                done=is_done,
                reward=reward
            )
            
        except Exception as e:
            return MyObservation(
                result=f"Error processing action: {str(e)}",
                success=False,
                done=True,
                reward=0.0
            )
    
    @property
    def state(self) -> State:
        """
        Return current episode metadata.
        
        NOTE: This is a @property, NOT a method.
        Access it as: env.state (not env.state())
        """
        return self._state
    
    # ──── Private helpers (your domain logic) ────
    
    def _initialize_scenario(self) -> dict:
        """Set up the scenario for a new episode."""
        # TODO: Implement your scenario setup
        return {}
    
    def _execute_action(self, action: MyAction):
        """Execute domain-specific action logic."""
        # TODO: Implement your action processing
        return "Action processed", 0.5, False
```

---

### 📁 server/app.py — The FastAPI Server (THE GATEWAY)

```python
"""
server/app.py — Creates the FastAPI server.

This is the entry point that Docker runs.
It wires your Environment to HTTP/WebSocket endpoints.
"""
from openenv.core.env_server import create_app
from models import MyAction, MyObservation
from server.my_environment import MyEnvironment

# ┌─────────────────────────────────────────────────┐
# │ CRITICAL: Pass the CLASS, not an instance!       │
# │                                                  │
# │ create_app(MyEnvironment, ...)   ← CORRECT      │
# │ create_app(MyEnvironment(), ...) ← WRONG!        │
# │                                                  │
# │ Why? Each WebSocket connection needs its OWN     │
# │ Environment instance for session isolation.      │
# └─────────────────────────────────────────────────┘

app = create_app(
    MyEnvironment,       # CLASS, not instance
    MyAction,            # Action type
    MyObservation,       # Observation type
    env_name="my_env"    # Name used in routing
)

# ──────────────────────────────────────────────
# ADD CUSTOM ENDPOINTS FOR HACKATHON
# These are REQUIRED by the hackathon rules
# ──────────────────────────────────────────────

@app.get("/tasks")
async def get_tasks():
    """Return list of tasks + action schemas."""
    return {
        "tasks": [
            {
                "name": "easy_task",
                "difficulty": "easy",
                "description": "...",
                "action_schema": { ... }
            },
            {
                "name": "medium_task",
                "difficulty": "medium",
                "description": "...",
                "action_schema": { ... }
            },
            {
                "name": "hard_task",
                "difficulty": "hard",
                "description": "...",
                "action_schema": { ... }
            },
        ]
    }

@app.post("/grader")
async def run_grader(episode_data: dict):
    """Score a completed episode. Returns float in [0.0, 1.0]."""
    try:
        score = compute_grade(episode_data)
        return {"score": max(0.0, min(1.0, float(score)))}
    except Exception as e:
        return {"score": 0.0, "error": str(e)}

@app.post("/baseline")
async def run_baseline():
    """Run baseline inference on all 3 tasks, return scores."""
    scores = {}
    for task in ["easy", "medium", "hard"]:
        try:
            scores[task] = run_baseline_for_task(task)
        except Exception:
            scores[task] = 0.0
    return {"scores": scores}
```

**What `create_app()` gives you automatically:**
- `GET /health` — health check
- `WebSocket /ws` — persistent session endpoint
- `POST /reset` — reset environment
- `POST /step` — take an action
- `GET /state` — get current state
- Optional web UI at `/web` (if `ENABLE_WEB_INTERFACE=true`)

---

### 📁 client.py — The Client (FOR USERS & BASELINE)

```python
"""
client.py — How agents connect to your environment.

This is used by:
1. Your baseline inference script
2. Anyone who wants to use your environment
3. RL training frameworks (TRL, torchforge, etc.)
"""
from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State
from .models import MyAction, MyObservation


class MyEnv(EnvClient[MyAction, MyObservation, State]):
    """
    Client for connecting to MyEnvironment server.
    
    Usage (async — recommended for training):
        async with MyEnv(base_url="https://...") as client:
            result = await client.reset()
            result = await client.step(MyAction(command="..."))
    
    Usage (sync — simpler, good for baseline script):
        with MyEnv(base_url="https://...").sync() as client:
            result = client.reset()
            result = client.step(MyAction(command="..."))
    """
    
    def _step_payload(self, action: MyAction) -> dict:
        """Convert Action to dict for WebSocket transmission."""
        return {
            "command": action.command,
            "parameters": action.parameters
        }
    
    def _parse_result(self, payload: dict) -> StepResult[MyObservation]:
        """Parse server response into StepResult."""
        obs_data = payload.get("observation", {})
        obs = MyObservation(
            result=obs_data.get("result", ""),
            success=obs_data.get("success", False),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )
    
    def _parse_state(self, payload: dict) -> State:
        """Parse state response."""
        return State(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
        )
```

---

### 📁 server/Dockerfile — Container Definition (MANDATORY)

```dockerfile
# Multi-stage build using openenv-base
# DO NOT change the base image!
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Copy environment code
COPY . /app/env

WORKDIR /app/env

# Install dependencies using uv (fast Python package manager)
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --no-editable; \
    else \
        uv sync --no-install-project --no-editable; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-editable; \
    else \
        uv sync --no-editable; \
    fi

# Final runtime stage
FROM ${BASE_IMAGE}
WORKDIR /app

COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"

# Health check — OpenEnv checks /health
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["sh", "-c", "cd /app/env && uvicorn server.app:app --host 0.0.0.0 --port 8000"]
```

---

### 📁 Hackathon-Specific Files (YOU ADD THESE)

#### `graders/grader_easy.py`
```python
def grader_easy(trajectory: list) -> float:
    """
    Score an episode for the easy task.
    
    RULES:
    - MUST return float in [0.0, 1.0]
    - MUST support partial credit (not just 0/1)
    - MUST be deterministic (same input → same output)
    - MUST handle empty trajectory (return 0.0)
    """
    if not trajectory:
        return 0.0
    
    # Example: multi-component partial credit
    accuracy = compute_accuracy(trajectory)     # 0.0 - 1.0
    efficiency = compute_efficiency(trajectory)  # 0.0 - 1.0
    
    score = accuracy * 0.7 + efficiency * 0.3
    return max(0.0, min(1.0, float(score)))  # ALWAYS clip!
```

#### `baseline/run_baseline.py`
```python
"""
Baseline inference script.
Runs a simple agent on all 3 tasks and prints scores.
"""
import argparse
from my_env import MyEnv, MyAction

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True)  # MUST be required
args = parser.parse_args()

for task_name in ["easy", "medium", "hard"]:
    try:
        with MyEnv(base_url=args.base_url).sync() as client:
            result = client.reset()
            # Simple baseline: take random/heuristic actions
            while not result.done:
                action = MyAction(command="default_action")
                result = client.step(action)
            
            score = get_grader_score(task_name, result)
            print(f"Task {task_name} score: {score:.4f}")
    except Exception as e:
        print(f"Task {task_name} score: 0.0000  (error: {e})")

exit(0)  # MUST exit 0 on success
```

---

## 6. Data Flow — A Complete Episode {#6-data-flow}

Here's exactly what happens during one complete interaction:

```
Step 1: Agent connects via WebSocket
──────────────────────────────────────
Agent                                    Server
  │                                       │
  │── WebSocket connect /ws ─────────────►│
  │                                       │ Server spawns new MyEnvironment()
  │◄── Connection accepted ──────────────│
  │                                       │

Step 2: Agent starts episode
──────────────────────────────────────
  │── {"action": "reset"} ──────────────►│
  │                                       │ env.reset() called
  │                                       │ → New UUID for episode_id
  │                                       │ → Initialize domain state
  │◄── {"observation": {...},            │
  │     "done": false,                   │
  │     "reward": 0.0} ─────────────────│
  │                                       │

Step 3: Agent takes actions (loop)
──────────────────────────────────────
  │── {"action": "step",                │
  │    "command": "diagnose",           │
  │    "parameters": {...}} ────────────►│
  │                                       │ env.step(action) called
  │                                       │ → Process domain logic
  │                                       │ → Calculate reward
  │◄── {"observation": {...},            │
  │     "done": false,                   │
  │     "reward": 0.3} ─────────────────│
  │                                       │
  │── [more steps...] ──────────────────│
  │                                       │

Step 4: Episode ends
──────────────────────────────────────
  │── {"action": "step", ...} ──────────►│
  │                                       │ env.step() detects completion
  │◄── {"observation": {...},            │
  │     "done": true,                    │
  │     "reward": 0.8} ─────────────────│
  │                                       │

Step 5: Grading
──────────────────────────────────────
  │── POST /grader {trajectory} ────────►│
  │                                       │ grader(trajectory) called
  │◄── {"score": 0.73} ─────────────────│
```

---

## 7. Graders & Reward Functions {#7-graders}

### The Difference

| | Per-Step Reward | Episode Grader |
|--|----------------|----------------|
| **When** | After every `step()` | After episode ends (`done=True`) |
| **Purpose** | Guide learning in real-time | Evaluate overall performance |
| **Range** | Any float | Must be float in [0.0, 1.0] |
| **Returned by** | `step()` → `Observation.reward` | `/grader` endpoint |
| **Partial credit** | Yes | MUST have partial credit |

### Writing Good Graders

**BAD — Binary scoring (will lose points):**
```python
def grader_bad(trajectory):
    if all_correct(trajectory):
        return 1.0
    return 0.0  # No partial credit!
```

**GOOD — Multi-component partial credit:**
```python
def grader_good(trajectory):
    if not trajectory:
        return 0.0
    
    # Component 1: Accuracy (70% weight)
    correct_actions = sum(1 for t in trajectory if t.was_correct)
    accuracy = correct_actions / len(trajectory)
    
    # Component 2: Efficiency (20% weight)
    optimal_steps = 5
    efficiency = max(0, 1 - (len(trajectory) - optimal_steps) / optimal_steps)
    
    # Component 3: Completion (10% weight)
    completion = 1.0 if trajectory[-1].done else 0.0
    
    score = accuracy * 0.7 + efficiency * 0.2 + completion * 0.1
    return max(0.0, min(1.0, float(score)))  # ALWAYS CLIP
```

### Difficulty Scaling

| Difficulty | Random Agent Score | Good Agent Score | What Makes It Harder |
|-----------|-------------------|-----------------|---------------------|
| Easy | ~0.3 (30% of the time) | 0.8 - 1.0 | Fewer choices, clearer signals |
| Medium | ~0.05-0.10 | 0.6 - 0.9 | More choices, subtler signals |
| Hard | < 0.01 | 0.5 - 0.8 | Many choices, requires strategy |

---

## 8. Deployment Pipeline {#8-deployment}

### The Complete Flow

```
1. DEVELOP LOCALLY
   └── openenv init my_env
   └── Edit models.py, my_environment.py, etc.
   └── openenv serve  (local dev server)
   └── Test with curl / client.py

2. BUILD DOCKER IMAGE
   └── openenv build
   └── docker run -p 8000:8000 openenv-my_env
   └── Test all endpoints

3. VALIDATE
   └── openenv validate --verbose
   └── Fix any issues → go to step 2

4. DEPLOY TO HUGGING FACE
   └── openenv push [--repo-id username/my_env]
   └── Wait for Space to build (~5 min)

5. VERIFY DEPLOYED
   └── curl https://your-space.hf.space/health → 200
   └── curl -X POST https://your-space.hf.space/reset → valid JSON
   └── python baseline/run_baseline.py --base-url https://your-space.hf.space

6. SUBMIT
   └── Paste HF Space URL into submission form
   └── DEADLINE: April 7, 2026 — 11:59 PM IST
```

### openenv CLI Commands

| Command | What It Does |
|---------|-------------|
| `openenv init my_env` | Scaffold new project with all template files |
| `openenv serve` | Start local dev server for testing |
| `openenv build` | Build Docker image (auto-detects context) |
| `openenv validate --verbose` | Check environment structure + spec compliance |
| `openenv push` | Deploy to HuggingFace Spaces |

---

## 9. Common Pitfalls & How to Avoid Them {#9-pitfalls}

### 🔴 Critical Mistakes (auto-disqualification)

| Mistake | Fix |
|---------|-----|
| `pip install openenv` | Use `pip install openenv-core` |
| `create_fastapi_app(env)` | Use `create_app(EnvClass, ...)` from `openenv.core.env_server` |
| Passing instance to `create_app()` | Pass the CLASS: `create_app(MyEnvironment, ...)` |
| `def state(self):` | Must be `@property` + `def state(self):` |
| Grader returns `int` | Must return `float`: `return 1.0` not `return 1` |
| Step never returns `done=True` | Add max_steps safety limit |
| Hardcoded `localhost` in baseline | Use `--base-url` argument |

### 🟡 Quality Mistakes (lower score)

| Mistake | Fix |
|---------|-----|
| Binary rewards (0 or 1 only) | Use multi-component partial credit formula |
| All tasks same action schema | Make each task's actions distinct |
| No error handling in `step()` | Wrap ALL logic in try/except |
| Missing README sections | Must have all 6 sections (see RULES.md) |
| Action is free-text string | Use structured Pydantic fields |

### 🟢 Things People Forget

| Item | Reminder |
|------|---------|
| `openenv.yaml` | Must list all tasks, endpoints, schema |
| `/health` endpoint | Provided by `create_app()` automatically |
| Episode isolation | State MUST NOT leak between episodes |
| Seed reproducibility | `reset(seed=42)` twice → identical episodes |

---

## 10. Quick Reference Cheat Sheet {#10-cheat-sheet}

### Import Map

```python
# Environment base class
from openenv.core.env_server.interfaces import Environment

# Data types
from openenv.core.env_server.types import Action, Observation, State

# Server creation
from openenv.core.env_server import create_app

# Client base class
from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
```

### Method Signatures

```python
class MyEnvironment(Environment):
    def __init__(self): ...
    def reset(self, seed=None) -> MyObservation: ...
    def step(self, action: MyAction) -> MyObservation: ...
    
    @property
    def state(self) -> State: ...
```

### CLI Quick Reference

```bash
pip install openenv-core       # install
openenv init my_env            # scaffold
openenv serve                  # local dev
openenv build                  # docker build
openenv validate --verbose     # check compliance
openenv push                   # deploy to HF
```

### Endpoint Map

| Endpoint | Method | Built-in? | What It Returns |
|----------|--------|-----------|-----------------|
| `/health` | GET | ✅ Yes | 200 OK |
| `/ws` | WebSocket | ✅ Yes | Persistent session |
| `/reset` | POST | ✅ Yes | Observation |
| `/step` | POST | ✅ Yes | Observation |
| `/state` | GET | ✅ Yes | State |
| `/web` | GET | ✅ Optional | Web UI |
| `/tasks` | GET | ❌ You add | Task list |
| `/grader` | POST | ❌ You add | Float score |
| `/baseline` | POST | ❌ You add | All task scores |

### Deadline Countdown

```
📅 Submission opens: March 28, 2026
⏰ HARD DEADLINE:    April 7, 2026 — 11:59 PM IST
🏟️ Finale:           April 25-26, 2026 (Bangalore)
```
