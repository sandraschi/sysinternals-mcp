"""Tests for sigcheck parser."""

from sysinternals_mcp.tools.sigcheck import _parse_csv

_CSV_SAMPLE = (
    '"path","verified","publisher","description"\n'
    '"C:\\\\Windows\\\\System32\\\\notepad.exe",'
    '"Signed","Microsoft Windows","Notepad"\n'
)


def test_parse_csv():
    result = _parse_csv(_CSV_SAMPLE)
    assert result["success"] is True
    assert result["count"] == 1
    assert result["files"][0]["verified"] == "Signed"


def test_parse_csv_empty():
    result = _parse_csv("")
    assert result["count"] == 0
