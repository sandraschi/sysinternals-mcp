"""Tests for du parser."""

from sysinternals_mcp.tools.du import _parse_du

_TEXT = """Du v2.1 - Directory disk usage reporter
Copyright (C) 2005-2024 Mark Russinovich
256000 C:\\Users
128000 C:\\Users\\test
128000 C:\\Users\\test\\Documents
Total:             512000 bytes
"""


def test_parse():
    result = _parse_du(_TEXT)
    assert result["success"] is True
    assert result["directory_count"] >= 2
    for d in result["directories"]:
        assert "size_bytes" in d
        assert "path" in d


def test_parse_empty():
    result = _parse_du("")
    assert result["directory_count"] == 0
