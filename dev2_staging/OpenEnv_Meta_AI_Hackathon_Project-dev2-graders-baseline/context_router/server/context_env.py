# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
server/context_env.py — Edge GPU Context Router Environment.

SACRED FILE PATH — matches TEAM_RULEBOOK Section 1, C2:
  Env class name: ContextRouterEnv
  Env file path:  server/context_env.py

Owner: Dev 1 (TEAM_RULEBOOK Section 0).
Dev 2 must NEVER edit this file.

PHASE 0 STATUS: STUB ONLY — reset() and step() return placeholder observations.
Full simulation logic is implemented in Phase B.
"""

import logging
import random
from typing import Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import CacheAction, CacheObservation, MemoryBlockInfo
except (ModuleNotFoundError, ImportError):
    from models import CacheAction, CacheObservation, MemoryBlockInfo

logger = logging.getLogger(__name__)


class ContextRouterEnv(Environment):
    """
    KV-cache eviction policy simulator for local LLMs on edge GPUs.

    Simulates a GPU memory manager where an RL agent must decide which
    KV-cache memory blocks to evict, retain, or compress to maximise
    throughput while preventing out-of-memory (OOM) events.

    RULES enforced here (TEAM_RULEBOOK):
      - @property above def state                    (PA1)
      - episode_id generated in reset(), NOT __init__  (PA2)
      - self._rng = random.Random(seed), NOT random.seed()  (PA3)
      - step() wraps ALL logic in try/except         (PA4)
      - MAX_STEPS class constant = 50                (PA4)
    """

    MAX_STEPS: int = 50   # class constant — infinite episodes are forbidden

    def __init__(self) -> None:
        """
        Initialise lightweight state.
        episode_id is created in reset() — NEVER here (rulebook PA2).
        """
        self._state: State = State(episode_id="unset", step_count=0)
        self._rng: random.Random = random.Random()
        # Simulation state (initialised properly in reset())
        self._vram_max: float = 16.0          # GB — simulated VRAM capacity
        self._vram_used: float = 0.0          # GB — current usage
        self._memory_blocks: list[MemoryBlockInfo] = []

    def reset(self, seed: Optional[int] = None) -> CacheObservation:
        """
        Start a new episode.

        RULE (PA2): Fresh UUID every call — state from prior episodes must NOT carry over.
        RULE (PA3): Seed via random.Random(seed), never random.seed().
        """
        if seed is not None:
            self._rng = random.Random(seed)   # local RNG — no global state

        # Fresh episode ID every reset (RULE PA2)
        self._state = State(
            episode_id=str(uuid4()),
            step_count=0,
        )

        # Initialise simulated memory — Phase B will replace with real logic
        self._vram_used = self._rng.uniform(0.3, 0.6) * self._vram_max
        self._memory_blocks = self._generate_initial_blocks()

        return CacheObservation(
            vram_utilization=self._vram_used / self._vram_max,
            incoming_tokens=0,
            memory_blocks=list(self._memory_blocks),
            oom_triggered=False,
            message="Environment reset. Ready for first action.",
            done=False,
            reward=0.0,
        )

    def step(self, action: CacheAction) -> CacheObservation:
        """
        Process one agent action.

        RULE (PA4): ALL logic wrapped in try/except — never a bare raise.
        RULE: episode must eventually end (MAX_STEPS enforced).
        """
        try:
            self._state = State(
                episode_id=self._state.episode_id,
                step_count=self._state.step_count + 1,
            )

            # Max-steps guard (RULE — infinite episodes forbidden)
            if self._state.step_count >= self.MAX_STEPS:
                return CacheObservation(
                    vram_utilization=self._vram_used / self._vram_max,
                    incoming_tokens=0,
                    memory_blocks=list(self._memory_blocks),
                    oom_triggered=False,
                    message="Max steps reached. Episode ended.",
                    done=True,
                    reward=float(self._compute_partial_credit()),
                )

            # ── PHASE B: Replace stub below with real simulation logic ──
            incoming = self._rng.randint(50, 400)
            reward, oom = self._apply_action_stub(action, incoming)

            return CacheObservation(
                vram_utilization=self._vram_used / self._vram_max,
                incoming_tokens=incoming,
                memory_blocks=list(self._memory_blocks),
                oom_triggered=oom,
                message=f"step {self._state.step_count}: tactic={action.tactic.value}",
                done=oom or self._state.step_count >= self.MAX_STEPS,
                reward=float(reward),
            )

        except Exception as e:
            logger.error(f"step() error: {e}", exc_info=True)
            return CacheObservation(
                vram_utilization=self._vram_used / self._vram_max,
                incoming_tokens=0,
                memory_blocks=list(self._memory_blocks),
                oom_triggered=False,
                message=f"invalid action: {e}",
                done=True,
                reward=0.0,
            )

    @property
    def state(self) -> State:
        """
        Current episode metadata.

        RULE (PA1): @property MUST be present above def state — checked before every commit.
        """
        return self._state

    # ── Private helpers — Phase B will expand these ───────────────────────────

    def _generate_initial_blocks(self) -> list[MemoryBlockInfo]:
        """Generate a small set of initial memory blocks (Phase B stub)."""
        return [
            MemoryBlockInfo(
                block_id=i,
                block_type=self._rng.choice(["kv_cache", "activations"]),
                attention_score=round(self._rng.uniform(0.0, 1.0), 4),
                token_count=self._rng.randint(64, 512),
                age=self._rng.randint(0, 10),
            )
            for i in range(self._rng.randint(3, 8))
        ]

    def _apply_action_stub(self, action: CacheAction, incoming: int):
        """Stub action application — Phase B replaces this with real logic."""
        # Simulate VRAM change
        block_ids = [b.block_id for b in self._memory_blocks]
        if action.target_block_id in block_ids:
            reward = 0.5
        else:
            reward = 0.0
        oom = self._vram_used / self._vram_max > 0.95
        return reward, oom

    def _compute_partial_credit(self) -> float:
        """Return partial credit at episode end — Phase B extends this."""
        return max(0.0, min(1.0, 1.0 - (self._vram_used / self._vram_max)))
