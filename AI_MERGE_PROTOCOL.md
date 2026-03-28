# AI_MERGE_PROTOCOL.md
> **Purpose:** A strict, non-negotiable set of instructions that I (the AI) must execute every time a merge between Dev 1 and Dev 2 is requested. This ensures the `TEAM_RULEBOOK.md` is never violated, and no silent assumptions are made.

---

## 1. PRE-MERGE VALIDATION (Stop on Failure)
Before writing any code or merging any branch into the `main` directory, the AI must verify:
1. **Target Branch/Code:** What branch or folder is being synced? (e.g., `dev2/graders-baseline`).
2. **File Ownership (Rulebook Section 0):** Identify who owns the files being merged.
   - `server/context_env.py` → Dev 1 Only.
   - `graders/*.py` and `server/app.py` → Dev 2 Only.
   - `models.py` / `openenv.yaml` → Both.
3. **Data Contract Intact:** Verify that `models.py` has not been altered on the incoming branch. If it has, **STOP** and alert the user immediately.
4. **Git Tracking & Binaries:** Run `git ls-files` to check if any large binaries (e.g., `git-portable.exe`) are being tracked (even if in `.gitignore`). If they are, run `git rm --cached <file>` before the merge to prevent 20+ minute hang times.
5. **Import Paths:** Verify that the incoming branch's test/grader scripts use `from models import ...` instead of `from context_router.models import ...` to avoid test execution failures due to mismatch with local `PYTHONPATH` scope.

## 2. THE MERGE EXECUTION
When merging code from the incoming branch to the local directory:
1. **DO NOT blindly copy and paste entire files if they are cross-owned.** Always selectively extract functions/endpoints into the correct file.
2. **Conflict Resolution is strictly Human-First (Rulebook G4).** If the AI detects a conflict in logic (e.g., Dev 2 accidentally modified `ContextRouterEnv` inside `app.py`, or Dev 1 modified a grader), the AI must **STOP** and output the conflicting code sections directly to the user.
   > **Directive:** *“I detected a merge conflict in [File]. Dev X attempted to modify it, but Dev Y owns it. I am not making assumptions. Please tell me which version to keep.”*
   - Note: Watch out for older Phase A scaffolds (short stubs) attempting to overwrite completed Phase B code. (See MISTAKES.md Rule 18).
3. **Never apply generic git merge commands without reviewing the incoming diff.**

## 3. POST-MERGE VERIFICATION LOOP (Rulebook Section 8)
Once code is merged locally, the AI must run the following checks. **No commits or pushes are allowed until all checks pass.**

1. **Type Check & Imports:** Look for broken imports (e.g., `__init__.py` faults).
2. **Unit Tests:** Execute `python -m pytest tests/ -v`. Must result in 0 errors.
3. **Integration Smoke Test:** Execute `python tests/integration_point_1.py`. Grader must return a `float` between `0.0` and `1.0`.
4. **Official Validator:** Execute `openenv validate --verbose`. Must log `[OK]`.

## 4. END-OF-MERGE PROCEDURES
1. **Update `MISTAKES.md`:** Append a new session log detailing exactly what files were merged and if any bugs occurred during the verification loop.
2. **Update Last Known Good State:** Change endpoints/tests from `NO` to `YES`.
3. **Push Notification:** Inform the user exactly what files need to be staged. 
4. Output the **AI Session Summary** block required by Rulebook Section 9.

---
> **AI Self-Enforcement:** I will read and apply this protocol automatically whenever the phrase "merge the code", "sync Dev 2", or "integrate the branches" is used.
