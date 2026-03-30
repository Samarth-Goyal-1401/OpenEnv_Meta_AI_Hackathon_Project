---
title: Context Router Environment
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
---

# Edge GPU Context Router - OpenEnv Environment

## Overview
Edge GPU Context Router simulates memory management for local LLM inference under VRAM pressure.
The agent decides which memory block to `evict`, `retain`, or `compress` to keep usage stable
while preserving critical context (`system_prompt`, `code_snippet`).

## Setup Instructions (for local testing)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000
```
