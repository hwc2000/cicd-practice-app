#!/usr/bin/env python3
"""CLI wrapper for agent_tools.patch_candidate."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_tools.patch_candidate import main


if __name__ == "__main__":
    main()
