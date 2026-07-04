"""Tests for coreinfo parser."""

from sysinternals_mcp.tools.coreinfo import _parse_coreinfo

_TEXT = """Coreinfo v3.6 - CPU information
Copyright (C) 2008-2024 Mark Russinovich
Intel(R) Core(TM) i9-13900K
x86/AMD64
Logical to Physical Processor Map:
*--- Physical 0
-*-- Physical 1
Feature flags:
*    SSE3
     MONITOR
*    SSSE3
"""


def test_parse():
    result = _parse_coreinfo(_TEXT)
    assert result["success"] is True
    assert "cpu_topology" in result
    assert "features" in result
