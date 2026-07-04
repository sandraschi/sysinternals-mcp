"""Tests for psfile parser."""

from sysinternals_mcp.tools.psfile import _parse_psfile

_TEXT = """PsFile v1.1 - Copyright (C) 1999-2024 Mark Russinovich
Sysinternals

C:\\Users\\test\\document.txt:
User:      remote-user
Locks:     1
Access:    Read
"""


def test_parse():
    result = _parse_psfile(_TEXT)
    assert result["success"] is True
    assert result["count"] >= 1
