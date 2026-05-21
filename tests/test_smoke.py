"""
Smoke tests for the quill-mcp package.

These don't replace manual end-to-end testing on a clean machine
(see CONTRIBUTING.md). They catch the basic regressions that would
ship a broken wheel to PyPI:

  - Package is shape-correct: imports work, console script is installed
  - Advisor backend builds without a runtime exception
  - MCP server speaks JSON-RPC and registers all four tools

Run with: pytest tests/
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest


# --- Import-level smoke ---------------------------------------------------


def test_server_module_imports():
    """The server module loads without exceptions (advisor builds, tools
    register, no import-order bugs)."""
    import quill_mcp.server  # noqa: F401


def test_all_four_tools_are_defined():
    """Each tool function still exists in the module — guards against
    accidental rename or deletion."""
    from quill_mcp import server

    for tool_name in ("quill_consult", "quill_perspective",
                       "quill_assumptions", "quill_mosaic"):
        assert hasattr(server, tool_name), f"Missing tool: {tool_name}"


def test_mcp_object_exists():
    from quill_mcp.server import mcp
    assert mcp is not None
    assert mcp.name == "quill"


# --- Console-script + protocol smoke -------------------------------------


CONSOLE_SCRIPT = shutil.which("quill-mcp")


@pytest.mark.skipif(
    CONSOLE_SCRIPT is None,
    reason="quill-mcp not on PATH — install with `pip install -e .` first",
)
def test_console_script_speaks_mcp_protocol():
    """Spawn `quill-mcp`, complete the MCP initialize handshake, and
    confirm tools/list returns the four expected tools.

    This is the test that catches 'the wheel installs but the entry
    point is broken' regressions.
    """
    initialize = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "quill-smoketest", "version": "0.0"},
        },
    })
    initialized = json.dumps({
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    })
    list_tools = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })

    env = os.environ.copy()
    env.update({
        "ADVISOR_BACKEND": "api",
        "AI_BASE_URL": "http://fake.invalid",
        "AI_API_KEY": "fake-key-for-tests",
        "AI_MODEL": "fake-model",
    })

    proc = subprocess.Popen(
        [CONSOLE_SCRIPT],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(
            input="\n".join([initialize, initialized, list_tools]) + "\n",
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        pytest.fail(
            f"quill-mcp didn't respond within 15s.\n"
            f"stdout: {stdout!r}\nstderr: {stderr!r}"
        )

    responses = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    tools_response = next(
        (r for r in responses if r.get("id") == 2), None
    )
    assert tools_response is not None, (
        f"No tools/list response received.\n"
        f"All responses: {responses}\nstderr: {stderr}"
    )
    assert "result" in tools_response, f"tools/list errored: {tools_response}"

    tool_names = {t["name"] for t in tools_response["result"]["tools"]}
    expected = {"quill_consult", "quill_perspective",
                "quill_assumptions", "quill_mosaic"}
    missing = expected - tool_names
    assert not missing, (
        f"Tools missing from server: {missing}. Got: {tool_names}"
    )
