# TECH STACK & SETUP — Zero Margin for Error

> **Purpose:** Strict versioning and environment setup guide to ensure local development exactly matches the HuggingFace deployment environment. Deviating from these versions is the #1 cause of deployment failure.

---

## 1. The Core Stack (MANDATORY VERSIONS)

| Component | Allowed Versions | Why? |
|-----------|------------------|------|
| **Python** | `3.10`, `3.11`, or `3.12` | OpenEnv does not support 3.13+. HuggingFace Spaces default to 3.10/3.11. |
| **OpenEnv**| `openenv-core` (latest) | **DO NOT** `pip install openenv`. The package is `openenv-core`. |
| **Server** | `fastapi`, `uvicorn` | Required for the `create_app` WebSocket+HTTP server. |
| **Models** | `pydantic` | Required for Action/Observation schema validation mapping. |
| **Package**| `uv` | Used by the official Dockerfile template for ultra-fast, deterministic builds. |

---

## 2. Forbidden Technologies (DO NOT USE)

❌ **GPU Libraries:** `torch`, `tensorflow`, `cuda-*`  
*(Your environment is a simulation server, NOT a training agent. Adding these will bloat your Docker image and cause HF Spaces to crash/timeout).*

❌ **Heavy Data Science:** `pandas`, `scipy` (unless strictly necessary)  
*(Use built-in Python or lightweight libraries whenever possible to keep the container small and fast).*

❌ **External Live APIs:** e.g., calling live OpenAI, live stock tickers in `step()`  
*(Graders must be deterministic. If an external API fails or changes, your environment breaks and you are disqualified).*

---

## 3. Local Setup Sequence (Do This First)

Run these exact commands to set up an isolated, safe local environment:

```bash
# 1. Verify Python version (MUST be 3.10, 3.11, or 3.12)
python --version

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows activation:
.venv\Scripts\activate
# Mac/Linux activation:
# source .venv/bin/activate

# 3. Upgrade pip and install uv
pip install --upgrade pip
pip install uv

# 4. Install the framework
pip install openenv-core fastapi uvicorn pydantic

# 5. Verify installation
openenv --help

# 6. Authenticate with HuggingFace (You need this to deploy later)
pip install huggingface_hub
huggingface-cli login
# (Paste your token from https://huggingface.co/settings/tokens)

# 7. Clone the official OpenEnv repo for reference examples
git clone https://github.com/meta-pytorch/OpenEnv
# Study: OpenEnv/envs/echo_env/ first, then coding_env/

# 8. Clone the prep course
git clone https://github.com/raun/openenv-course
```

---

## 4. Docker & Containerization

The hackathon requires your environment to run in Docker. The `openenv init` command provides the correct Dockerfile.

**Golden Rules for Docker:**
1. **Never** change the base image from `ARG BASE_IMAGE=openenv-base:latest`.
2. Do not use local volume mounts in the final Dockerfile.
3. Manage all Python dependencies inside `pyproject.toml`, which the Dockerfile will install via `uv sync`.

**To test your Docker build locally:**
```bash
# Must be run from inside your environment folder
openenv build
```
