# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Client for the Context Router Environment.
"""

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient
from openenv.core.env_server.types import State

from .models import CacheAction, CacheObservation


class MyEnv(EnvClient[CacheAction, CacheObservation, State]):
    """
    Client for connecting to ContextRouterEnv server.
    """

    def _step_payload(self, action: CacheAction) -> dict:
        """Convert a CacheAction to a dict for the HTTP/WebSocket request."""
        return {
            "target_block_id": action.target_block_id,
            "tactic": action.tactic.value,
        }

    def _parse_result(self, payload: dict) -> StepResult[CacheObservation]:
        """Convert the HTTP/WebSocket response to a CacheObservation."""
        obs_payload = payload.get("observation", {})
        
        # Memory blocks come as dicts, parse to objects if needed (Pydantic handles this mostly)
        blocks = obs_payload.get("memory_blocks", [])

        obs = CacheObservation(
            vram_utilization=obs_payload.get("vram_utilization", 0.0),
            incoming_tokens=obs_payload.get("incoming_tokens", 0),
            memory_blocks=blocks,
            oom_triggered=obs_payload.get("oom_triggered", False),
            message=obs_payload.get("message", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> State:
        """Parse state dictionary into State model."""
        return State(
            episode_id=payload.get("episode_id", "unset"),
            step_count=payload.get("step_count", 0),
        )
