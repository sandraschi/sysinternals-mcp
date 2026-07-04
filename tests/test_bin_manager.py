"""Tests for BinaryManager."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from sysinternals_mcp.bin_manager import TOOLS, BinaryManager


def test_cache_dir_default():
    bm = BinaryManager(cache_dir="/tmp/sysint-test")  # noqa: S108
    assert "sysint-test" in str(bm.path("autorunsc"))


def test_exe_name_mapping():
    bm = BinaryManager(cache_dir="/tmp/sysint-test")  # noqa: S108
    mapping = {
        "autorunsc": "Autorunsc.exe",
        "handle64": "handle64.exe",
        "pslist": "pslist.exe",
        "listdlls": "listdlls.exe",
        "tcpvcon": "tcpvcon.exe",
        "sigcheck": "sigcheck64.exe",
        "accesschk": "accesschk64.exe",
        "psloggedon": "PsLoggedon.exe",
        "psfile": "psfile64.exe",
        "coreinfo": "Coreinfo.exe",
        "du": "du64.exe",
        "psinfo": "PsInfo.exe",
    }
    for name, expected in mapping.items():
        assert bm.path(name).name == expected, f"{name} -> {expected}"


def test_scan_cached_empty():
    bm = BinaryManager(cache_dir="/tmp/empty-sysint")  # noqa: S108
    cached = bm.scan_cached()
    for name in TOOLS:
        assert cached[name]["cached"] is False


def test_eula_acceptance():
    tmp = Path(tempfile.mkdtemp()) / "sysint-eula"
    bm = BinaryManager(cache_dir=str(tmp))
    assert bm.eula_accepted() is False
    bm.accept_eula()
    assert bm.eula_accepted() is True


@patch("sysinternals_mcp.bin_manager.subprocess.run")
def test_run_handles_args(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    bm = BinaryManager(cache_dir="/tmp/sysint-test")  # noqa: S108
    bm_path = bm.path("pslist")
    bm_path.parent.mkdir(parents=True, exist_ok=True)
    bm_path.write_text("fake binary")
    bm.accept_eula()
    bm.run("pslist", ["-nobanner"])
    call_args = mock_run.call_args[0][0]
    assert "-accepteula" in call_args
    assert str(bm_path) in call_args[0]
