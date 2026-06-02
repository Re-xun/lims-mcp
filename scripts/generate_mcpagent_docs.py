#!/usr/bin/env python3
"""Compatibility wrapper for the MCP agent docs workflow."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.mcpagent_docs.cli import main
from workflow.mcpagent_docs.config import *  # noqa: F403 - legacy constants
from workflow.mcpagent_docs.generator import *  # noqa: F403 - legacy import surface


if __name__ == "__main__":
    main()
