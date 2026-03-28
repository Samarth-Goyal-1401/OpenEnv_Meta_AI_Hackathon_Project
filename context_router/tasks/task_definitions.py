from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ContextRouterTask(BaseModel):
    task_id: str = Field(..., description="Unique task identifier (easy, medium, hard)")
    description: str = Field(..., description="Human-readable description of the task requirements")
    max_steps: int = Field(50, description="Maximum allowed steps per episode")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Environment-specific configuration parameters")

TASKS: List[ContextRouterTask] = [
    ContextRouterTask(
        task_id="easy",
        description="Low incoming token volume, static retention. Survive 50 steps without OOM.",
        max_steps=50,
        kwargs={"token_arrival_rate": 10, "peak_vram_limit": 0.5}
    ),
    ContextRouterTask(
        task_id="medium",
        description="Burst token arrivals with dynamic block ages. Requires selective eviction.",
        max_steps=50,
        kwargs={"token_arrival_rate": 50, "peak_vram_limit": 0.75}
    ),
    ContextRouterTask(
        task_id="hard",
        description="High token volume, tight VRAM constraints. Requires optimal block compression and eviction.",
        max_steps=50,
        kwargs={"token_arrival_rate": 200, "peak_vram_limit": 0.9}
    )
]
