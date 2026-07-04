"""Tests for psloggedon parser."""

from sysinternals_mcp.tools.psloggedon import _parse_psloggedon

_TEXT = """PsLoggedon v1.35

Users logged on locally:
NT AUTHORITY\\SYSTEM               Local
SANDRA-PC\\sandra                  Console
"""


def test_parse():
    result = _parse_psloggedon(_TEXT)
    assert result["success"] is True


def test_parse_empty():
    result = _parse_psloggedon("")
    assert result["count"] == 0
