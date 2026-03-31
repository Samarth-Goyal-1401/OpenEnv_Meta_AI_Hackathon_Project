#!/usr/bin/env python3
"""
Repo-root baseline entrypoint for the HF deployment artifact.
"""

import asyncio

from baseline.run_baseline import main


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
