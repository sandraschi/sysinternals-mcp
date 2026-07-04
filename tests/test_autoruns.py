"""Tests for autorunsc parser."""

from sysinternals_mcp.tools.autoruns import _parse_csv

_CSV_SAMPLE = (
    '"Entry","Description","Enabled","Date","Publisher","Image Path"\n'
    '"HKLM\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run\\\\SecurityHealth",'
    '"Windows Security notification icon","enabled","","Microsoft Windows",'
    '"C:\\\\Windows\\\\System32\\\\SecurityHealthSystray.exe"\n'
    '"HKLM\\\\SYSTEM\\\\CurrentControlSet\\\\Services\\\\WpnService",'
    '"Windows Push Notification System","enabled","","Microsoft Windows",'
    '"C:\\\\Windows\\\\System32\\\\svchost.exe"\n'
)


def test_parse_csv():
    result = _parse_csv(_CSV_SAMPLE)
    assert result["success"] is True
    assert result["count"] == 2
    assert result["entries"][0]["Publisher"] == "Microsoft Windows"


def test_parse_csv_empty():
    result = _parse_csv("")
    assert result["success"] is True
    assert result["count"] == 0
