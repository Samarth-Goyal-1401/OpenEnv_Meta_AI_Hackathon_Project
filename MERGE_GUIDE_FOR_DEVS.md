# The OpenEnv Fast-Merge Guide 🚀

This is the definitive, hard-learned guide to executing a lightning-fast, conflict-free merge between Dev 1 (Shreyas) and Dev 2 (Samarth) without the AI or terminal freezing.

> [!CAUTION]
> **READ BEFORE YOU BRANCH**  
> Always run `git fetch` and `git pull origin main` BEFORE you begin your branch. This ensures you are not building on top of stale scaffolds (like the 185-line stub) and accidentally overwriting your teammate's completed 394-line code.

---

## 🛠️ Step 1: Pre-Commit Checklist (For the Dev)
Before you even type `git push`, the developer must verify the following:

1. **Fix Absolute Imports:** Ensure your newly added files (graders, tests, etc.) do not use absolute imports that break the local `PYTHONPATH` during tests. 
   - ❌ `from context_router.models import CacheObservation`
   - ✅ `from models import CacheObservation`
2. **Check for Bloated Binaries:** Have you downloaded large `.exe` or `.zip` files into the directory? 
   - Even if they are in `.gitignore`, if you previously tracked them, Git will hang trying to push 60MB files. 
   - **Fix:** If you accidentally tracked a giant file, run `git rm --cached <filename.exe>` before you commit.

## 🔐 Step 2: The Credential Setup
Do not rely on the hidden Windows Git Credential Helper. It will spawn invisible background windows (`git-credential-helper-selector.exe`) that freeze terminal sessions infinitely.

**Instead, always use a Personal Access Token (PAT):**
1. Ensure your GitHub PAT has the **`repo`** scope checkbox explicitly ticked.
2. If pushing to your teammate's repository, make sure you have explicitly clicked **Accept Invite** in your email or at `https://github.com/<Teammate>/<Repo>/invitations`. Otherwise, GitHub will throw a `403 Permission Denied` error even if the PAT is valid.
3. Keep your PAT ready to paste to the AI when requested.

## 🤖 Step 3: The AI Merge Command
When you are ready to merge, simply tell the AI:
> *"Perform the Merge Ceremony for Phase [X]. Bring in Dev [X]'s remote branch into main. Here is my PAT: `ghp_...`"*

### What the AI will do automatically:
1. Verify the Data Contract (`models.py`) is intact and unchanged.
2. Read `TEAM_RULEBOOK.md` to cleanly separate Dev 1's owned logic from Dev 2's owned logic.
3. Run the automated Verification Loop (`pytest`, Smoke Tests, `openenv validate`).
4. Append Mistake / Session Logs to `MISTAKES.md`.
5. Push instantly using your PAT directly encoded in the command (`git push https://<PAT>@github.com...`), bypassing hidden Windows GUI blockers entirely.

---

> [!TIP]
> **Need to manually kill frozen Git processes?**
> If your powershell ever gets stuck again on push, kill the hidden credential prompts with:
> `taskkill /F /IM "git-credential-helper-selector.exe" /T`
