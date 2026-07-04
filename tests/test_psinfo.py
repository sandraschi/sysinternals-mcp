"""Tests for psinfo parser."""

from sysinternals_mcp.tools.psinfo import _parse_psinfo

_TEXT = """PsInfo v1.79 - Local and Remote System Information
Copyright (C) 2002-2024 Mark Russinovich
System information for \\\\SANDRA-PC:
Uptime:                   7 days 3 hours 12 minutes 45 seconds
OS:                       Microsoft Windows 11 Pro
OS Version:               10.0.22631
Hotfixes:
KB5034441
KB5034843
"""


def test_parse():
    result = _parse_psinfo(_TEXT)
    assert result["success"] is True
    assert "sections" in result
    assert "raw" in result


def test_parse_system_section():
    result = _parse_psinfo(_TEXT)
    sys_section = result.get("sections", {})
    keys = list(sys_section.keys())
    assert len(keys) > 0
