# STRATEGIC COMPACTION — Performance & Memory Management

> **Source:** Adapted from the `everything-claude-code` session lifecycle system.
> **Purpose:** To manage long-running sessions (like your current 12+ hour session) and keep the agent (me) sharp, responsive, and token-efficient.

---

## 1. Why Compact?
As a session grows (more tool calls, more terminal output), the "context window" fills up. This causes:
- **Losing Focus:** The agent might forget early research or rules.
- **Latency:** Responses take longer to generate.
- **Cost/Token Bloat:** Each message becomes more expensive.

---

## 2. When to Compact
*Trigger: Use this when a session reaches ~50+ turns or lasts > 6 hours.*

**Your Current Session:** 12h 40m (High Priority for Compaction).

---

## 3. The Compaction Workflow (How to Restart)
To "compact" this session and start fresh without losing any progress, follow these 4 steps:

### Step A: Update the "Memory Files"
Before restarting, we must ensure these files are 100% up-to-date:
1.  **`MISTAKES.md`**: Log every "Gotcha" and fixed bug from this session.
2.  **`RULES.md`**: Update any immutable constraints discovered.
3.  **`task.md`**: Mark all completed items with `[x]`.

### Step B: Generate the "Context Snapshot"
Ask the agent (me): 
> "Summarize the current state of the project, the last known good state of every file, and the exact next step for a fresh session."

### Step C: Start a Fresh Session
Close this terminal/chat and open a new one in the same directory.

### Step D: Reload the "Brain"
In the new session, give the agent this single command:
> "Read `SYSTEM_PROMPT.md`, `RULES.md`, and `MISTAKES.md`. Reference the snapshot from the previous session. Resume from [Next Step]."

---

## 4. What Survives Compaction?
Only what is written to **Files**.
- ✅ **Files:** `server/`, `models.py`, `RULES.md`, etc.
- ✅ **Documentation:** `SYSTEM_PROMPT.md`, `OPENENV_COMPLETE_GUIDE.md`.
- ❌ **Terminal History:** All past command outputs.
- ❌ **Ephemeral Chat:** All conversational context not in files.

**Recommendation:** Since we have just finished the research/prep phase, **now is the perfect time to compact.** We have written all the "Brain" files. A fresh session will be much faster for the actual implementation phase.
