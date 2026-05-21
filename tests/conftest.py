"""
Set fake advisor env before any test imports quill_mcp.server.

The server calls build_advisor() at module-import time. Without these,
imports would fail with "ADVISOR_BACKEND=api requires AI_BASE_URL...".
We never actually call the advisor in tests — just confirm the server
loads and speaks MCP protocol.
"""

import os

os.environ.setdefault("ADVISOR_BACKEND", "api")
os.environ.setdefault("AI_BASE_URL", "http://fake.invalid")
os.environ.setdefault("AI_API_KEY", "fake-key-for-tests")
os.environ.setdefault("AI_MODEL", "fake-model")
