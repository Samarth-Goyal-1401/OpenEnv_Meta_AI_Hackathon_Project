# Teammate Handoff — Phase 0 Complete

Welcome Shreyas. Phase 0 (Scaffolding & Data Contract) is complete and verified by Samarth (Dev 2).

## 🚀 Startup Instructions for Dev 1

Follow these steps exactly (TEAM_RULEBOOK Section 2):

1. **Clone & Setup**:
   ```bash
   git clone https://github.com/Samarth-Goyal-1401/OpenEnv_Meta_AI_Hackathon_Project.git
   cd OpenEnv_Meta_AI_Hackathon_Project/context_router
   ```
2. **Install Dependencies**:
   - Preferred: `uv sync` (if you have `uv` installed)
   - Alternative: `pip install -r requirements.txt`
3. **Verify Local Setup**:
   ```bash
   openenv validate --verbose
   ```
   (Should show 0 errors)

## 🏗️ The Data Contract (Frozen)

This is the `models.json` contract for our environment. **Do not change field names.**

```json
{
  "action_class": "CacheAction",
  "action_fields": ["target_block_id:int", "tactic:EvictionTactic"],
  "observation_class": "CacheObservation",
  "observation_fields": [
    "vram_utilization:float",
    "incoming_tokens:int",
    "memory_blocks:list",
    "oom_triggered:bool",
    "message:str"
  ],
  "observation_inherited_fields": ["done:bool", "reward:float"],
  "tasks": ["easy", "medium", "hard"],
  "max_steps": 50
}
```

## 📅 Next Steps for Dev 1 (Simulation Logic)

1. **Simulation Logic**: Build out the real [server/context_env.py](file:///c:/Users/Saksham/Desktop/meta_hackathon/context_router/server/context_env.py) logic.
2. **Determinism**: Ensure [reset(seed=42)](file:///c:/Users/Saksham/Desktop/meta_hackathon/context_router/server/context_env.py#67-96) is deterministic (RULE PA3).
3. **Internal State**: Implement the VRAM management logic and block tracking.

## 📂 File Ownership Reminder

| File | Owner |
|------|-------|
| [server/context_env.py](file:///c:/Users/Saksham/Desktop/meta_hackathon/context_router/server/context_env.py) | **Dev 1** (You) |
| `graders/` | **Samarth (Dev 2)** |
| `baseline/` | **Samarth (Dev 2)** |
| [models.py](file:///c:/Users/Saksham/Desktop/meta_hackathon/context_router/models.py) | **Both (Sync required)** |
