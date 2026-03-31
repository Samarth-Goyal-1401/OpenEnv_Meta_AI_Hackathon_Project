# Deep Sanitation Audit Log (2026-03-31)

## Scope Reviewed
- `context_router` (server endpoints, environment logic, graders, client, Docker)
- `hf_deployment` (server endpoints, environment logic, graders, client, Docker)
- `tests/` and package manifests for consistency checks

## Findings and Actions

1. Issue: `/grader` silently accepted unknown `task_id` values by defaulting to `easy`.
- Risk: Incorrect scoring behavior and hidden client-side bugs.
- Fix: Added explicit task validation and now return HTTP 422 for unsupported task IDs.
- Files:
  - `context_router/server/app.py`
  - `hf_deployment/server/app.py`

2. Issue: `/grader` accepted unbounded trajectory payload sizes.
- Risk: Potential memory/CPU abuse (request amplification / DoS vector).
- Fix: Added strict trajectory length cap (`MAX_GRADER_TRAJECTORY_LEN = 512`) and explicit rejection.
- Files:
  - `context_router/server/app.py`
  - `hf_deployment/server/app.py`

3. Issue: Invalid trajectory element payloads were swallowed and returned score `0.0`.
- Risk: Opaque failure mode that hides malformed API usage and weakens contract safety.
- Fix: Added typed payload rejection path (HTTP 422) for malformed trajectory items, preserving `0.0` fallback only for unexpected internal failures.
- Files:
  - `context_router/server/app.py`
  - `hf_deployment/server/app.py`

4. Issue: Docker runtime containers ran as root.
- Risk: Elevated blast radius in case of compromise.
- Fix: Added dedicated non-root runtime user (`uid 10001`) and ownership handoff.
- Files:
  - `context_router/server/Dockerfile`
  - `context_router/Dockerfile`
  - `hf_deployment/Dockerfile`

5. Issue: Docker healthchecks relied on `curl`.
- Risk: Tooling dependency mismatch in minimal images and larger attack surface if installing extra OS packages.
- Fix: Replaced healthcheck command with a Python stdlib TCP port check (`socket.create_connection`) to remove curl dependency and avoid hardcoded URL strings.
- Files:
  - `context_router/server/Dockerfile`
  - `context_router/Dockerfile`
  - `hf_deployment/Dockerfile`

6. Issue: One Docker build path installed dependencies without excluding dev extras.
- Risk: Larger image size and unnecessary packages in runtime.
- Fix: Updated dependency sync to `--no-dev` in `context_router/Dockerfile`.
- Files:
  - `context_router/Dockerfile`

## Notes
- Existing test suites passed before and after sanitation changes.
- No use of `eval`, `exec`, `os.system`, unsafe deserialization (`pickle.loads`), or shell-injection patterns found in scanned project code.
- Both service trees are intentionally mirrored; endpoint hardening changes were applied to both to avoid drift.
