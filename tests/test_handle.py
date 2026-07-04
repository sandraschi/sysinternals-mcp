"""Tests for handle64 parser."""

from sysinternals_mcp.tools.handle import _parse_handle_text

_HANDLE_SAMPLE = """Handle v5.0
Copyright (C) 2024 Mark Russinovich
Sysinternals

456: C:\\Users\\test\\file.txt  File   0xFFFF
789: C:\\Windows\\system32\\dll.dll  Section  0xABC
"""


def test_parse_handle():
    result = _parse_handle_text(_HANDLE_SAMPLE)
    assert result["success"] is True
    assert result["count"] >= 1
    assert result["handles"][0]["pid"] == 456
    assert result["handles"][0]["type"] == "File"


def test_parse_handle_empty():
    result = _parse_handle_text("Handle v5.0\nCopyright\n")
    assert result["count"] == 0
