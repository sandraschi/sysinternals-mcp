"""Tests for native RAMMap tools."""

import pytest
from fastmcp import FastMCP

from sysinternals_mcp.tools.rammap import (
    _parse_memory_categories,
    _parse_process_memory,
    _query_nt_memory_list,
    register_tool,
)


def test_query_nt_memory_list():
    data = _query_nt_memory_list()
    if data is not None:
        assert "categories" in data
        assert "totals" in data
        assert "standby_priorities_mb" in data
        assert data["categories"]["TOTAL_MB"] > 0
        assert data["categories"]["STANDBY_MB"] >= 0
        assert len(data["standby_priorities_mb"]) == 8


@pytest.mark.asyncio
async def test_registered_tools_execution():
    app = FastMCP("TestApp")
    register_tool(app)

    # Test physical memory query
    phys_res = await app.call_tool("rammap_physical", {"detailed": True})
    assert phys_res.structured_content["success"] is True
    assert phys_res.structured_content["totals"]["total_mb"] > 0
    assert "STANDBY_MB" in phys_res.structured_content["categories"]
    assert phys_res.structured_content["method"] == "ntdll_native"

    # Test process listing
    procs_res = await app.call_tool("rammap_processes", {"top_n": 5})
    assert procs_res.structured_content["success"] is True
    assert procs_res.structured_content["count"] <= 5
    if procs_res.structured_content["processes"]:
        p = procs_res.structured_content["processes"][0]
        assert "WS_MB" in p
        assert "PID" in p

    # Test file backed / cache
    files_res = await app.call_tool("rammap_file_backed", {})
    assert files_res.structured_content["success"] is True
    assert "cache_total_mb" in files_res.structured_content

    # Test summary
    summary_res = await app.call_tool("rammap_summary", {})
    assert summary_res.structured_content["success"] is True
    assert "physical" in summary_res.structured_content
    assert "top_processes" in summary_res.structured_content

    # Test empty standby list (runs or gracefully returns elevation message)
    empty_res = await app.call_tool("rammap_empty", {"target": "standby"})
    assert "success" in empty_res.structured_content


def test_parse_memory_categories_fallback():
    mock_text = """
TOTAL_MB:32768
AVAILABLE_MB:16384
USED_MB:16384
CACHE_MB:8192
STANDBY_MB:4096
MODIFIED_MB:512
FREE_MB:11776
PAGEFILE_TOTAL_MB:4096
PAGEFILE_USED_MB:1024
"""
    parsed = _parse_memory_categories(mock_text, detailed=False)
    assert parsed["success"] is True
    assert parsed["totals"]["total_mb"] == 32768
    assert parsed["totals"]["standby_mb"] == 4096


def test_parse_process_memory():
    mock_json = '[{"PID": 100, "Name": "test.exe", "WS_MB": 120.5}]'
    parsed = _parse_process_memory(mock_json, top_n=10)
    assert parsed["success"] is True
    assert parsed["count"] == 1
    assert parsed["processes"][0]["PID"] == 100
