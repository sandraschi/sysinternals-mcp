"""Tests for listdlls parser."""

from sysinternals_mcp.tools.listdlls import _parse_listdlls

_SAMPLE = """svchost.exe pid: 1234
0x7ffe0000 0x1000 ntdll.dll 10.0.22621.1
0x7ffd0000 0x1000 kernel32.dll 10.0.22621.1

explorer.exe pid: 5678
0x7ffe0000 0x1000 ntdll.dll 10.0.22621.1
0x7ffd0000 0x1000 shell32.dll 10.0.22621.1
"""


def test_parse_listdlls():
    result = _parse_listdlls(_SAMPLE)
    assert result["success"] is True
    assert result["count"] == 2
    for proc in result["processes"]:
        assert "dlls" in proc
        assert "dll_count" in proc


def test_parse_listdlls_empty():
    result = _parse_listdlls("")
    assert result["count"] == 0
