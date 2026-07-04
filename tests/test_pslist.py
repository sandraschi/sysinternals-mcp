"""Tests for pslist parser."""

from sysinternals_mcp.tools.pslist import _parse_pslist

_PSLIST_SAMPLE = """PsList v1.4 - Process Information Lister
Copyright (C) 2009-2024 Mark Russinovich
Sysinternals - www.sysinternals.com

Process information for SANDRA-PC:

Name                Pid Pri Thd  Hnd   VM        WS      Priv     CPU Time    Elapsed Time
Idle                0   0   4    0     0         8       0        96:34:12.234 31:22:10.578
System              4   8   167  15256 366848    1008    2296     1:45:06.780  31:22:10.578
smss                384 11  2    34    512       436     540      0:00:00.015  31:22:10.578
"""


def test_parse_pslist():
    result = _parse_pslist(_PSLIST_SAMPLE)
    assert result["success"] is True
    assert result["count"] >= 2


def test_parse_pslist_fields():
    result = _parse_pslist(_PSLIST_SAMPLE)
    for proc in result["processes"]:
        assert "pid" in proc
        assert "name" in proc
        assert "handles" in proc
        assert "threads" in proc


def test_parse_pslist_empty():
    result = _parse_pslist("")
    assert result["count"] == 0
