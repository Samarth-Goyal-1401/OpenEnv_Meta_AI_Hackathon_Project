# HACKATHON SUBMISSION FLIGHT CHECKLIST

> **Status:** MANDATORY BEFORE APRIL 7, 11:59 PM IST
> **Rule:** If ANY of these checkboxes are empty, DO NOT hit submit.

---

## 🔲 1. The Disqualification Zero-Tolerance Check
*These checks are run automatically by scripts. If they fail, humans will never see your code.*

- [ ] `openenv validate --verbose` runs with **0 errors**.
- [ ] HuggingFace Space deployed and `ping https://<your-space>.hf.space/health` returns `HTTP 200 OK`.
- [ ] `reset()` called on your live Space returns a valid JSON `Observation`.
- [ ] Docker builds successfully (`openenv build`).
- [ ] `openenv.yaml` exists at the root, is valid, and matches your python types.
- [ ] Target domain is **NOT** a classic game (no Chess, Tic-Tac-Toe, Snake).

## 🔲 2. The Golden Ratio (The 3 Tasks)
*Checking the core OpenEnv requirements.*

- [ ] You have exactly 1 Environment Class.
- [ ] You have exactly 3 tasks listed in `openenv.yaml` (Easy, Medium, Hard).
- [ ] The `/tasks` endpoint returns a HTTP 200 with the 3 tasks and their action schemas.
- [ ] The action schemas in `/tasks` have distinct properties (not just identical raw strings for all 3).
- [ ] The `/grader` endpoint accepts a trajectory and returns a `{"score": X.X}` where X.X is between 0.0 and 1.0.

## 🔲 3. The Baseline Script Proof
*Proving your environment is playable.*

- [ ] `baseline/run_baseline.py` exists.
- [ ] It accepts a `--base-url` argument.
- [ ] It plays all 3 tasks sequentially.
- [ ] It catches exceptions so a failure on Task 1 doesn't crash the script before Task 2.
- [ ] It prints out 3 final `float` scores clearly to the console.
- [ ] It `exit(0)` on success.

## 🔲 4. The Defensive Programming Check
*Agents do stupid things. Your server must never crash.*

- [ ] **NO BARE `raise`**: Your `step()` function does not contain unhandled `raise ValueError(...)`.
- [ ] **NO SILENT FAILS**: You do not use `except: pass` in your logic.
- [ ] **DETERMINISM**: Calling `reset(seed=42)` twice yields the exact same scenario.
- [ ] **STATE BLEED**: `episode_id` is a newly generated UUID inside every single `reset()` call.
- [ ] **BOUNDARIES**: Grader scores are strictly wrapped in `max(0.0, min(1.0, score))`.
- [ ] **MAX STEPS**: You have a hard-coded maximum step limit in `step()` to prevent infinite episodes (e.g., reaching 50 steps forces `done=True`).

## 🔲 5. The "Wow Factor" (Human Judging)
*Once scripts pass, humans grade these specific elements.*

- [ ] **README Completeness:** Action Space documented? Observation Space documented? Reward formulas written out in math/text? Setup instructions clear?
- [ ] **Partial Credit:** Your medium/hard task graders do not just return 0.0 or 1.0. They return 0.3, 0.7, etc., based on partial success.
- [ ] **Semantic Meaning:** Your variables aren't named `x1`, `y2`. They are named `patient_heart_rate`, `server_load_percentage`, etc.
- [ ] **Clean Git:** No API keys, no `.venv`, no ` outputs/` logs committed to the repository or HuggingFace Space.

## 🔲 6. The Final Run (Exact Sequence)
Run this **exact sequence** one last time before submitting the URL. Every command must succeed.

```bash
# Step 1: Build Docker image from scratch
openenv build

# Step 2: Run the container
docker run -p 8000:8000 openenv-<env_name>

# Step 3: Test all required endpoints
curl -X POST http://localhost:8000/reset          # Must return valid JSON Observation
curl http://localhost:8000/tasks                   # Must list 3 tasks
curl -X POST http://localhost:8000/grader          # Must return {"score": X.XX}
curl -X POST http://localhost:8000/baseline        # Must return all 3 task scores

# Step 4: Run baseline script (the judge's automated check)
python baseline/run_baseline.py --base-url http://localhost:8000
# Must: exit 0, print 3 scores, all scores must be floats

# Step 5: Final spec validation
openenv validate --verbose
# Must: 0 errors

# Step 6: Deploy
openenv push

# Step 7: Confirm the live Space works
curl -X POST https://<your-space>.hf.space/reset  # Must return 200
python baseline/run_baseline.py --base-url https://<your-space>.hf.space
```
