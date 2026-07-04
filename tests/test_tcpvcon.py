"""Tests for tcpvcon parser."""

from sysinternals_mcp.tools.tcpvcon import _parse_csv

# tcpvcon uses -c CSV with headers: Protocol,LocalAddr,LocalPort,RemoteAddr,RemotePort,State,ProcessName,PID
_CSV = (
    "Protocol,LocalAddr,LocalPort,RemoteAddr,RemotePort,State,ProcessName,PID\n"
    "TCP,192.168.1.1,49765,10.0.0.1,443,ESTABLISHED,chrome.exe,1234\n"
    "UDP,0.0.0.0,5355,*,*,UNKNOWN,svchost.exe,5678\n"
)


def test_parse_csv():
    result = _parse_csv(_CSV)
    assert result["success"] is True
    assert result["count"] == 2


def test_parse_csv_empty():
    result = _parse_csv("")
    assert result["success"] is True
    assert result["count"] == 0
