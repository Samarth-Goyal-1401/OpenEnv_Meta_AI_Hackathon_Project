# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
models.py — Frozen Data Contract for the Edge GPU Context Router.

IMMUTABLE after first commit to main.
Any change requires BOTH teammates present + openenv validate passing.
Schema version: 1  |  Git tag: schema-v1

Sacred field names (TEAM_RULEBOOK Section 1, C2):
  CacheAction:      target_block_id, tactic
  CacheObservation: vram_utilization, incoming_tokens, memory_blocks,
                    oom_triggered, message
                    (done + reward are INHERITED — never add them)
  MemoryBlockInfo:  block_id, block_type, attention_score, token_count, age
  Env class name:   ContextRouterEnv
  Env file path:    server/context_env.py
"""

from enum import Enum
from typing import List

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# EVICTION TACTIC — the only tactic enum the env and graders should reference
# ──────────────────────────────────────────────────────────────────────────────
class EvictionTactic(str, Enum):
    EVICT    = "evict"
    RETAIN   = "retain"
    COMPRESS = "compress"


# ──────────────────────────────────────────────────────────────────────────────
# ACTION — What the agent sends each step
# ──────────────────────────────────────────────────────────────────────────────
class CacheAction(Action):
    """
    One agent action: target a memory block and choose an eviction tactic.

    Sacred fields (do NOT rename):
      target_block_id : int
      tactic          : EvictionTactic
    """

    target_block_id: int = Field(
        ...,
        description="ID of the memory block to act on",
    )
    tactic: EvictionTactic = Field(
        ...,
        description="Eviction tactic to apply (evict | retain | compress)",
    )


# ──────────────────────────────────────────────────────────────────────────────
# MEMORY BLOCK INFO — one element of the memory_blocks list in CacheObservation
# ──────────────────────────────────────────────────────────────────────────────
class MemoryBlockInfo(BaseModel):
    """
    Metadata for a single KV-cache memory block.

    Sacred fields (do NOT rename):
      block_id        : int
      block_type      : str
      attention_score : float
      token_count     : int
      age             : int
    """

    block_id:        int   = Field(..., description="Unique block identifier")
    block_type:      str   = Field(..., description="Block type (e.g. kv_cache, activations)")
    attention_score: float = Field(..., description="Attention weight for this block (0.0–1.0)")
    token_count:     int   = Field(..., description="Number of tokens stored in this block")
    age:             int   = Field(..., description="Steps since this block was last accessed")


# ──────────────────────────────────────────────────────────────────────────────
# OBSERVATION — What the agent receives after each step
#
# RULE (C4): done + reward must NEVER appear here.
#            They are inherited from openenv.core.env_server.types.Observation.
# ──────────────────────────────────────────────────────────────────────────────
class CacheObservation(Observation):
    """
    Observation returned by ContextRouterEnv after every step() and reset().

    Sacred fields (do NOT rename):
      vram_utilization : float
      incoming_tokens  : int
      memory_blocks    : List[MemoryBlockInfo]
      oom_triggered    : bool
      message          : str

    Inherited (do NOT redefine):
      done   : bool   ← from Observation base class
      reward : float  ← from Observation base class
    """

    vram_utilization: float               = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current VRAM utilisation as fraction of total capacity (0.0–1.0)",
    )
    incoming_tokens:  int                 = Field(
        ...,
        ge=0,
        description="Number of new tokens arriving this step",
    )
    memory_blocks:    List[MemoryBlockInfo] = Field(
        default_factory=list,
        description="Snapshot of all current memory blocks",
    )
    oom_triggered:    bool                = Field(
        False,
        description="Whether an out-of-memory event occurred this step",
    )
    message:          str                 = Field(
        "",
        description="Human-readable description of this step's outcome",
    )
