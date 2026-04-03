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

Owner: Dev 1 (Shreyas). Dev 2 must NEVER edit this file.

Simulates KV-cache memory management on edge GPUs running local LLMs.
The agent decides which memory blocks to evict, retain, or compress
when VRAM fills up during a long conversation.
"""

import logging
import random
from typing import Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import CacheAction, CacheObservation, MemoryBlockInfo, EvictionTactic
except (ModuleNotFoundError, ImportError):
    from models import CacheAction, CacheObservation, MemoryBlockInfo, EvictionTactic

logger = logging.getLogger(__name__)


class ContextRouterEnv(Environment):
    """
    KV-cache eviction policy simulator for local LLMs on edge GPUs.

    Rules enforced (TEAM_RULEBOOK):
      - @property above def state                       (PA1)
      - episode_id generated in reset(), NOT __init__   (PA2)
      - self._rng = random.Random(seed)                 (PA3)
      - step() wraps ALL logic in try/except            (PA4)
      - MAX_STEPS class constant = 50                   (PA4)
    """

    MAX_STEPS: int = 50
    ATTENTION_DECAY: float = 0.95
    COMPRESSION_RATIO: float = 0.5

    CRITICAL_TYPES = frozenset({"system_prompt", "code_snippet"})

    TASK_CONFIGS = {
        "easy": {
            "max_capacity": 8000,
            "num_initial_blocks": 10,
            "initial_utilization": 0.85,
            "incoming_token_range": (100, 200),
            "block_type_weights": [
                ("system_prompt", 1), ("code_snippet", 1),
                ("user_query", 2), ("small_talk", 6),
            ],
        },
        "medium": {
            "max_capacity": 10000,
            "num_initial_blocks": 20,
            "initial_utilization": 0.90,
            "incoming_token_range": (150, 350),
            "block_type_weights": [
                ("system_prompt", 1), ("code_snippet", 3),
                ("user_query", 4), ("assistant_response", 4),
                ("rag_context", 3), ("small_talk", 5),
            ],
        },
        "hard": {
            "max_capacity": 10000,
            "num_initial_blocks": 15,
            "initial_utilization": 0.80,
            "incoming_token_range": (200, 500),
            "rag_spike_step": 5,
            "rag_spike_tokens": 1000,
            "block_type_weights": [
                ("system_prompt", 1), ("code_snippet", 3),
                ("user_query", 3), ("assistant_response", 3),
                ("rag_context", 2), ("small_talk", 3),
            ],
        },
    }

    # ── Constructor ───────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._state: State = State(episode_id="unset", step_count=0)
        self._rng: random.Random = random.Random()
        self._current_task: str = "easy"
        self._max_capacity: int = 8000
        self._blocks: dict[int, MemoryBlockInfo] = {}
        self._next_block_id: int = 0
        self._incoming_tokens: int = 0
        self._compressed_ids: set[int] = set()
        self._initial_code_block_count: int = 0
        # Delayed penalty state (Task 3)
        self._critical_block_ids: set[int] = set()
        self._delayed_penalty_queue: list[tuple[int, int]] = []  # (trigger_step, block_id)
        # Dashboard state tracking
        self._last_message: str = ""
        self._last_reward: float = 0.0

    # ── Public API for Dev 2 ──────────────────────────────────────────────

    def set_task(self, task_name: str) -> None:
        """Set the current task difficulty. Call BEFORE reset()."""
        if task_name in self.TASK_CONFIGS:
            self._current_task = task_name

    # ── @property state (PA1) ─────────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    # ── reset() ───────────────────────────────────────────────────────────

    def reset(self, seed: Optional[int] = None) -> CacheObservation:
        """
        Start a new episode.

        RULE (PA2): Fresh UUID every call.
        RULE (PA3): Seed via random.Random(seed), never random.seed().
        """
        if seed is not None:
            self._rng = random.Random(seed)

        self._state = State(episode_id=str(uuid4()), step_count=0)

        config = self.TASK_CONFIGS[self._current_task]
        self._max_capacity = config["max_capacity"]
        self._blocks = {}
        self._next_block_id = 0
        self._compressed_ids = set()
        self._delayed_penalty_queue = []
        self._critical_block_ids = set()

        self._generate_initial_blocks(config)

        # Task 3: Mark 1-2 system_prompt blocks as hidden-critical
        system_block_ids = [
            bid for bid, b in self._blocks.items()
            if b.block_type in ("system_prompt", "code_snippet")
            and b.attention_score >= 0.6
        ]
        if system_block_ids:
            num_critical = min(2, len(system_block_ids))
            self._critical_block_ids = set(self._rng.sample(system_block_ids, num_critical))
            logger.info("Critical blocks for this episode: %s", self._critical_block_ids)

        self._initial_code_block_count = sum(
            1 for b in self._blocks.values() if b.block_type == "code_snippet"
        )
        self._incoming_tokens = self._rng.randint(*config["incoming_token_range"])

        total_tokens = self._total_tokens()
        self._last_message = "Environment reset. Ready for first action."
        self._last_reward = 0.0
        return CacheObservation(
            vram_utilization=self._clamp_util(total_tokens),
            incoming_tokens=self._incoming_tokens,
            memory_blocks=list(self._blocks.values()),
            oom_triggered=False,
            message=self._last_message,
            done=False,
            reward=0.0,
        )

    # ── step() ────────────────────────────────────────────────────────────

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

            # ── Max-steps guard ──
            if self._state.step_count >= self.MAX_STEPS:
                return self._obs(
                    done=True,
                    reward=self._compute_reward(),
                    message=f"Max steps ({self.MAX_STEPS}) reached.",
                )

            # ── Validate block_id (Task 4: fatal on invalid) ──
            if action.target_block_id not in self._blocks:
                return self._obs(
                    done=True, reward=0.0,
                    message="Invalid block_id selected. Fatal error.",
                )

            # ── Validate tactic for easy task (no compress) ──
            if (self._current_task == "easy"
                    and action.tactic == EvictionTactic.COMPRESS):
                return self._obs(
                    done=False, reward=0.0,
                    message="Compress not available in easy task. Step wasted.",
                )

            # ── 1) Execute tactic ──
            block = self._blocks[action.target_block_id]
            priority_msg = self._apply_priority_signal(action, block)
            msg = self._execute_tactic(action, block)
            if priority_msg:
                msg += f" | {priority_msg}"

            # ── 1b) Task 3: Check if evicted block was critical ──
            if (action.tactic == EvictionTactic.EVICT
                    and action.target_block_id in self._critical_block_ids):
                trigger_step = self._state.step_count + 5
                self._delayed_penalty_queue.append(
                    (trigger_step, action.target_block_id)
                )
                logger.info(
                    "Critical block %d evicted — hallucination queued for step %d",
                    action.target_block_id, trigger_step,
                )
                # No immediate penalty — the agent won't know yet

            # ── 2) Attention decay ──
            self._apply_attention_decay()

            # ── 3) Inject incoming tokens as a new block ──
            inject_msg = self._inject_incoming_block()
            if inject_msg:
                msg += f" | {inject_msg}"

            # ── 4) RAG spike (hard task, step 5) ──
            spike_msg = self._check_rag_spike()
            if spike_msg:
                msg += f" | {spike_msg}"

            # ── 4b) Task 3: Process delayed penalties ──
            penalty_result = self._process_delayed_penalties()
            if penalty_result:
                penalty_msg, penalty_reward = penalty_result
                msg += f" | {penalty_msg}"
                # Force reward to 0 and spike incoming tokens
                return self._obs(
                    done=False,
                    reward=0.0,
                    message=msg,
                )

            # ── 5) Generate next incoming tokens ──
            config = self.TASK_CONFIGS[self._current_task]
            self._incoming_tokens = self._rng.randint(*config["incoming_token_range"])

            # ── 6) OOM check ──
            total = self._total_tokens()
            if total > self._max_capacity:
                return self._obs(
                    done=True, reward=0.0, oom=True,
                    message=msg + " | OOM! Tokens exceeded capacity.",
                )

            return self._obs(
                done=False,
                reward=self._compute_reward(),
                message=msg,
            )

        except Exception as e:
            logger.error(f"step() error: {e}", exc_info=True)
            return CacheObservation(
                vram_utilization=0.0, incoming_tokens=0,
                memory_blocks=[], oom_triggered=False,
                message=f"Internal error: {e}",
                done=True, reward=0.0,
            )

    # ── Private helpers ───────────────────────────────────────────────────

    def _total_tokens(self) -> int:
        return sum(b.token_count for b in self._blocks.values())

    def _clamp_util(self, total: int) -> float:
        return max(0.0, min(1.0, total / self._max_capacity))

    def _obs(self, *, done: bool, reward: float, message: str,
             oom: bool = False) -> CacheObservation:
        total = self._total_tokens()
        self._last_message = message
        self._last_reward = float(max(0.0, min(1.0, reward)))
        return CacheObservation(
            vram_utilization=self._clamp_util(total),
            incoming_tokens=self._incoming_tokens,
            memory_blocks=list(self._blocks.values()),
            oom_triggered=oom,
            message=message,
            done=done,
            reward=self._last_reward,
        )

    def _execute_tactic(self, action: CacheAction, block: MemoryBlockInfo) -> str:
        bid = action.target_block_id

        if action.tactic == EvictionTactic.EVICT:
            del self._blocks[bid]
            return (f"Evicted block {bid} ({block.block_type}, "
                    f"{block.token_count} tokens freed)")

        if action.tactic == EvictionTactic.COMPRESS:
            if bid in self._compressed_ids:
                return f"Block {bid} already compressed. No effect."
            new_count = max(1, int(block.token_count * self.COMPRESSION_RATIO))
            self._blocks[bid] = MemoryBlockInfo(
                block_id=bid, block_type=block.block_type,
                attention_score=block.attention_score,
                token_count=new_count, age=block.age,
            )
            self._compressed_ids.add(bid)
            return (f"Compressed block {bid}: "
                    f"{block.token_count} → {new_count} tokens")

        # RETAIN
        return f"Retained block {bid} ({block.block_type})"

    def _apply_priority_signal(self, action: CacheAction, block: MemoryBlockInfo) -> str:
        """
        Hard-task-only signal:
        - aligned priority: no extra pressure
        - misaligned/missing priority: injects extra spill tokens
        This makes `priority` materially affect trajectories.
        """
        if self._current_task != "hard":
            return ""

        expected = self._expected_priority(block)
        if action.priority is None:
            spill = 160
            self._inject_priority_spill(spill)
            return (
                f"Hard priority missing (expected around {expected}). "
                f"Spill +{spill} tokens"
            )

        delta = abs(action.priority - expected)
        if delta <= 1:
            return f"Hard priority aligned ({action.priority} vs expected {expected})"

        spill = 80 if delta == 2 else 160
        self._inject_priority_spill(spill)
        return (
            f"Hard priority mismatch ({action.priority} vs expected {expected}). "
            f"Spill +{spill} tokens"
        )

    def _expected_priority(self, block: MemoryBlockInfo) -> int:
        score = 3
        if block.block_type in self.CRITICAL_TYPES:
            score += 1
        if block.attention_score >= 0.75:
            score += 1
        elif block.attention_score <= 0.25:
            score -= 1
        if block.age <= 2:
            score += 1
        elif block.age >= 12:
            score -= 1
        if block.token_count >= 700:
            score += 1
        elif block.token_count <= 150:
            score -= 1
        return max(1, min(5, score))

    def _inject_priority_spill(self, tokens: int) -> None:
        if tokens <= 0:
            return
        spill_block = MemoryBlockInfo(
            block_id=self._next_block_id,
            block_type="priority_spill",
            attention_score=0.15,
            token_count=tokens,
            age=0,
        )
        self._blocks[self._next_block_id] = spill_block
        self._next_block_id += 1

    def _apply_attention_decay(self) -> None:
        updated: dict[int, MemoryBlockInfo] = {}
        for bid, b in self._blocks.items():
            if b.block_type == "system_prompt":
                attn = 1.0
            else:
                attn = round(b.attention_score * self.ATTENTION_DECAY, 6)
            updated[bid] = MemoryBlockInfo(
                block_id=b.block_id, block_type=b.block_type,
                attention_score=attn, token_count=b.token_count,
                age=b.age + 1,
            )
        self._blocks = updated

    def _inject_incoming_block(self) -> str:
        if self._incoming_tokens <= 0:
            return ""
        btype = self._rng.choice(["user_query", "assistant_response", "small_talk"])
        new_block = MemoryBlockInfo(
            block_id=self._next_block_id, block_type=btype,
            attention_score=round(self._rng.uniform(0.3, 0.9), 4),
            token_count=self._incoming_tokens, age=0,
        )
        self._blocks[self._next_block_id] = new_block
        self._next_block_id += 1
        return f"New {btype} block ({self._incoming_tokens} tokens)"

    def _check_rag_spike(self) -> str:
        config = self.TASK_CONFIGS[self._current_task]
        spike_step = config.get("rag_spike_step", -1)
        if self._state.step_count != spike_step:
            return ""
        spike_tokens = config["rag_spike_tokens"]
        rag_block = MemoryBlockInfo(
            block_id=self._next_block_id, block_type="rag_context",
            attention_score=round(self._rng.uniform(0.5, 0.8), 4),
            token_count=spike_tokens, age=0,
        )
        self._blocks[self._next_block_id] = rag_block
        self._next_block_id += 1
        return f"RAG SPIKE: {spike_tokens} tokens injected!"

    def _compute_reward(self) -> float:
        """reward = 0.6 * critical_kept + 0.4 * vram_freed_ratio"""
        system_kept = any(
            b.block_type == "system_prompt" for b in self._blocks.values()
        )
        if not system_kept:
            critical_kept = 0.0
        else:
            if self._initial_code_block_count > 0:
                cur_code = sum(
                    1 for b in self._blocks.values()
                    if b.block_type == "code_snippet"
                )
                code_ratio = cur_code / self._initial_code_block_count
            else:
                code_ratio = 1.0
            critical_kept = 0.5 + 0.5 * code_ratio

        total = self._total_tokens()
        vram_freed = max(0.0, 1.0 - total / self._max_capacity)

        reward = 0.6 * critical_kept + 0.4 * vram_freed
        return float(max(0.0, min(1.0, reward)))

    def _process_delayed_penalties(self) -> tuple[str, float] | None:
        """Task 3: Fire delayed hallucination events when their trigger step arrives."""
        if not self._delayed_penalty_queue:
            return None

        current_step = self._state.step_count
        fired: list[int] = []
        remaining: list[tuple[int, int]] = []

        for trigger_step, block_id in self._delayed_penalty_queue:
            if current_step >= trigger_step:
                fired.append(block_id)
            else:
                remaining.append((trigger_step, block_id))

        self._delayed_penalty_queue = remaining

        if not fired:
            return None

        # HALLUCINATION event: spike incoming tokens to simulate runaway LLM
        spike_tokens = 800
        hallucination_block = MemoryBlockInfo(
            block_id=self._next_block_id,
            block_type="hallucination_spill",
            attention_score=0.1,
            token_count=spike_tokens,
            age=0,
        )
        self._blocks[self._next_block_id] = hallucination_block
        self._next_block_id += 1
        self._incoming_tokens += spike_tokens

        block_list = ", ".join(str(b) for b in fired)
        msg = (
            f"HALLUCINATION: Evicted critical block(s) [{block_list}] "
            f"caused context loss! +{spike_tokens} token spike."
        )
        logger.warning(msg)
        return msg, 0.0

    def _generate_initial_blocks(self, config: dict) -> None:
        num_blocks = config["num_initial_blocks"]
        target_total = int(config["initial_utilization"] * config["max_capacity"])
        weights = config["block_type_weights"]

        type_list: list[str] = []
        for btype, count in weights:
            type_list.extend([btype] * count)
        self._rng.shuffle(type_list)

        # System prompt is ALWAYS block 0
        if "system_prompt" in type_list:
            type_list.remove("system_prompt")
        type_list = ["system_prompt"] + type_list[: num_blocks - 1]

        base_tokens = target_total // num_blocks

        for btype in type_list:
            bid = self._next_block_id
            self._next_block_id += 1

            if btype == "system_prompt":
                tokens = max(256, base_tokens + self._rng.randint(100, 300))
                attn, age = 1.0, 0
            elif btype == "code_snippet":
                tokens = max(64, base_tokens + self._rng.randint(-50, 100))
                attn = round(self._rng.uniform(0.6, 0.95), 4)
                age = self._rng.randint(0, 8)
            elif btype == "small_talk":
                tokens = max(32, base_tokens + self._rng.randint(-200, -50))
                attn = round(self._rng.uniform(0.05, 0.3), 4)
                age = self._rng.randint(5, 20)
            elif btype == "rag_context":
                tokens = max(64, base_tokens + self._rng.randint(50, 200))
                attn = round(self._rng.uniform(0.4, 0.7), 4)
                age = self._rng.randint(1, 10)
            else:  # user_query, assistant_response
                tokens = max(32, base_tokens + self._rng.randint(-50, 50))
                attn = round(self._rng.uniform(0.3, 0.8), 4)
                age = self._rng.randint(0, 15)

            self._blocks[bid] = MemoryBlockInfo(
                block_id=bid, block_type=btype,
                attention_score=attn, token_count=tokens, age=age,
            )
