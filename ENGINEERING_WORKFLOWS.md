# ENGINEERING WORKFLOWS — "Zero Margin for Error"

> **Source:** Adapted from the `everything-claude-code` best practices.
> **Purpose:** Standardized workflows for research, development, and verification to eliminate bugs and ensure high-quality submissions.

---

## 1. SEARCH-FIRST (Research Before You Code)
*Trigger: Use this before starting any new feature or fixing a complex bug.*

**The Workflow:**
1.  **Define Need:** State exactly what functionality is required.
2.  **Lookup Docs:** Search the OpenEnv official docs (`meta-pytorch.org`) or repo first.
3.  **Find Examples:** Look for a similar implementation in the `openenv/envs/` directory.
4.  **Verify Assumptions:** Run a small script or one-off command to test a theory about how a framework tool works.
5.  **Draft Plan:** Only *after* research is complete, write the implementation plan.

**Why?** Prevents "hallucinating" API calls that don't exist (e.g., `create_fastapi_app` vs the correct `create_app`).

---

## 2. TDD FOR GRADERS (Test-Driven Graders)
*Trigger: Use this before implementing the `step()` logic for any task.*

**The Workflow:**
1.  **Define Success:** Write down in plain English what a 1.0, 0.5, and 0.0 score looks like for the task.
2.  **Write the Grader:** Implement the `grader_task.py` function.
3.  **Create Mock Trajectories:** Create a small test script with hardcoded "trajectories" (lists of observations/actions).
4.  **Verify Grader:** Run the tests.
    *   Does the "Perfect" mock return `1.0`?
    *   Does the "Fail" mock return `0.0`?
    *   Does the "Partial" mock return a `float` in between?
5.  **Implement Logic:** Now, and ONLY now, implement the `step()` function in your environment aimed at producing those trajectories.

**Why?** Ensures your scoring is fair and deterministic before you spend hours on simulation logic.

---

## 3. THE VERIFICATION LOOP (Pre-Flight)
*Trigger: Run this before every `openenv push` and before marking a task as "Done".*

| Phase | Command | Success Condition |
|-------|---------|-------------------|
| **1. Build** | `openenv build` | Docker image builds with 0 errors. |
| **2. Type Check** | `pyright .` or `mypy .` | 0 type errors in `models.py` and `server/`. |
| **3. Logic Check** | `curl -X POST /reset` | Local container returns valid JSON. |
| **4. Grader Check** | `/grader` (test script) | Returns `float` in `[0.0, 1.0]`. |
| **5. Baseline Check** | `python baseline/run_baseline.py` | Exits 0, all 3 scores printed. |
| **6. Spec Check** | `openenv validate --verbose` | 0 errors. |

**Why?** Catches 99% of "automated disqualification" triggers.

---

## 4. DESIGN FIRST (Architecture Decisions)
*Trigger: Use before running `openenv init`.*

1.  **Action Schema:** Define the exact JSON shape an agent sends.
2.  **Observation Schema:** Define the exact JSON shape an agent receives.
3.  **State Schema:** Define what *internal* variables the environment tracks (not visible to agent).
4.  **Reward Formula:** Write the math: `reward = (A * 0.7) + (B * 0.3)`.

**Why?** Mapping out the "data contract" prevents refactoring 5 files later when you realize you forgot a field.

---

## 5. YAML-PYTHON SYNC (Always Keep openenv.yaml Up to Date)
*Trigger: Run after every change to `models.py` or task definitions.*

**The Rule:**
- Every field added to `MyAction` or `MyObservation` MUST be reflected in `openenv.yaml`.
- Every task added to `task_definitions.py` MUST be reflected in `openenv.yaml`.
- After any sync, run `openenv validate --verbose` to confirm 0 errors.

**Why?** The automated judging system reads `openenv.yaml` to verify your submission. If your Python types and spec file diverge, you fail validation silently.
