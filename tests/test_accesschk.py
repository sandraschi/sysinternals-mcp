"""Tests for accesschk parser."""

from sysinternals_mcp.tools.accesschk import _parse_accesschk

_TEXT = """Accesschk v6.15 - Reports effective permissions
Copyright (C) 2006-2024 Mark Russinovich
Sysinternals

RW C:\\Users\\test
R  C:\\Windows
C:\\Program Files
"""


def test_parse():
    result = _parse_accesschk(_TEXT)
    assert result["success"] is True
    assert result["count"] >= 2
