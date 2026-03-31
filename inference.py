#!/usr/bin/env python3
"""
Root-level baseline entrypoint for automated submission checks.

Delegates to the existing Context Router baseline runner.
"""

import asyncio
import os
import sys


REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from context_router.baseline.run_baseline import main


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
