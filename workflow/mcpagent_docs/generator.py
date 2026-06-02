"""Compatibility exports for the MCP agent docs workflow.

The implementation lives in focused modules under ``workflow.mcpagent_docs``.
This module keeps older imports such as ``import generate_mcpagent_docs as base`` working.
"""

from __future__ import annotations

from .cli import main
from .io import *  # noqa: F403
from .inventory import *  # noqa: F403
from .naming import *  # noqa: F403
from .render_markdown import *  # noqa: F403
from .xml_extractors import *  # noqa: F403


if __name__ == "__main__":
    main()
