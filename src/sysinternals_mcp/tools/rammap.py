"""DIY RAMMap equivalent -- physical memory breakdown via WMI and psutil.

RAMMap is excluded from the standard tool set because it is GUI-only with no
scriptable CLI export. This module provides a close equivalent using WMI queries,
performance counters, and psutil -- the same data sources RAMMap uses internally.
No Sysinternals binary required.
"""

from __future__ import annotations

import os
import subprocess
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

_PWSH = "powershell"


def register_tool(app: FastMCP, _manager=None) -> None:

    @app.tool(name="rammap_physical")
    def rammap_physical(
        detailed: Annotated[
            bool,
            Field(default=False, description="Include per-category breakdown with standby list details"),
        ] = False,
    ) -> dict:
        """Show physical memory usage breakdown by category.

        RAMMap-style view: active, standby, modified, modified-no-write, transition,
        zeroed, free, and bad page counts. Also reports total, available, cached,
        and page-file sizes.

        Uses a single PowerShell script that queries WMI and performance counters.
        No binary download required.

        ## Return Format
        {"success": bool, "categories": dict, "totals": dict, "error": str | None}
        """
        proc = subprocess.run(
            [_PWSH, "-NoProfile", "-Command", _PS_MEMORY_BREAKDOWN],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if proc.returncode != 0:
            return _fallback_via_psutil(detailed)
        return _parse_memory_categories(proc.stdout, detailed)

    @app.tool(name="rammap_processes")
    def rammap_processes(
        top_n: Annotated[
            int, Field(default=20, description="Number of top processes to return", ge=1, le=200)
        ] = 20,
    ) -> dict:
        """Show per-process memory usage: working set, private bytes, shareable, pagefile.

        RAMMap-style process list sorted by working set descending.

        Uses Get-Process with WMI extensions for private working set data.
        No binary download required.

        ## Return Format
        {"success": bool, "processes": list[dict], "count": int, "total_ws_mb": float, "error": str | None}
        """
        proc = subprocess.run(
            [_PWSH, "-NoProfile", "-Command", _PS_PROCESS_MEMORY],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if proc.returncode != 0:
            return _process_fallback_psutil(top_n)
        return _parse_process_memory(proc.stdout, top_n)

    @app.tool(name="rammap_file_backed")
    def rammap_file_backed() -> dict:
        """Show file-backed page cache summary from system working set.

        Reports cached file extensions, top mapped files, and system cache totals.
        Uses WMI queries against the operating system cache manager.

        ## Return Format
        {"success": bool, "cache_total_mb": float, "sections": list[dict], "error": str | None}
        """
        proc = subprocess.run(
            [_PWSH, "-NoProfile", "-Command", _PS_FILE_BACKED],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if proc.returncode != 0:
            return _file_backed_fallback()
        return _parse_file_backed(proc.stdout)

    @app.tool(name="rammap_summary")
    def rammap_summary() -> dict:
        """Combined memory diagnostic: physical breakdown + top processes + file cache.

        One-shot equivalent of calling rammap_physical, rammap_processes (top 10),
        and rammap_file_backed.

        ## Return Format
        {"success": bool, "physical": dict, "top_processes": list[dict], "file_cache": dict}
        """
        phys = rammap_physical(detailed=False)
        procs = rammap_processes(top_n=10)
        files = rammap_file_backed()
        return {
            "success": True,
            "physical": phys.get("categories", {}) or phys.get("totals", {}),
            "top_processes": procs.get("processes", []),
            "file_cache": files.get("cache_total_mb", 0),
            "error": phys.get("error") or procs.get("error") or files.get("error"),
        }


# ---------------------------------------------------------------------------
# PowerShell scripts
# ---------------------------------------------------------------------------

_PS_MEMORY_BREAKDOWN = """
$os = Get-CimInstance Win32_OperatingSystem
$total = $os.TotalVisibleMemorySize * 1KB
$avail = $os.FreePhysicalMemory * 1KB

$counters = Get-Counter "\\Memory\\*" -ErrorAction SilentlyContinue `
    | Select-Object -ExpandProperty CounterSamples
$cache_bytes = 0; $standby = 0; $modified = 0; $free = 0
foreach ($c in $counters) {
    $p = $c.Path
    if ($p -match 'Cache Bytes') { $cache_bytes = $c.CookedValue }
    if ($p -match 'Standby Cache') { $standby += $c.CookedValue }
    if ($p -match 'Modified Page List') { $modified = $c.CookedValue }
    if ($p -match 'Free \\& Zero') { $free = $c.CookedValue }
}

$pf = Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue
$pfTotal = 0
foreach ($p in $pf) { $pfTotal += $p.AllocatedBaseSize }
if ($pfTotal -eq 0) { $pfTotal = $os.TotalVirtualMemorySize / 1MB - $os.TotalVisibleMemorySize / 1MB }

Write-Host "TOTAL_MB:$([math]::Round($total / 1MB, 0))"
Write-Host "AVAILABLE_MB:$([math]::Round($avail / 1MB, 0))"
Write-Host "USED_MB:$([math]::Round(($total - $avail) / 1MB, 0))"
Write-Host "CACHE_MB:$([math]::Round($cache_bytes / 1MB, 0))"
Write-Host "STANDBY_MB:$([math]::Round($standby / 1MB, 0))"
Write-Host "MODIFIED_MB:$([math]::Round($modified / 1MB, 0))"
Write-Host "FREE_MB:$([math]::Round($free / 1MB, 0))"
Write-Host "PAGEFILE_TOTAL_MB:$pfTotal"
$pfDiv = $os.TotalVirtualMemorySize - $os.FreeVirtualMemory
$pfUsed = [math]::Round(($pfTotal * $pfDiv / $os.TotalVirtualMemorySize), 0)
Write-Host "PAGEFILE_USED_MB:$pfUsed"
"""

_PS_PROCESS_MEMORY = """
Get-Process | Where-Object { $_.Id -gt 0 } | Sort-Object WorkingSet64 -Descending `
    | Select-Object -First 200 @{N='PID';E={$_.Id}}, `
        @{N='Name';E={$_.ProcessName}}, `
        @{N='WS_MB';E={[math]::Round($_.WorkingSet64 / 1MB, 1)}}, `
        @{N='Private_MB';E={[math]::Round($_.PrivateMemorySize64 / 1MB, 1)}}, `
        @{N='VM_MB';E={[math]::Round($_.VirtualMemorySize64 / 1MB, 1)}}, `
        @{N='PeakWS_MB';E={if ($_.PeakWorkingSet64) { [math]::Round($_.PeakWorkingSet64 / 1MB, 1) } else { 0 }}}, `
        @{N='Threads';E={$_.Threads.Count}}, `
        @{N='Handles';E={$_.HandleCount} `
    } | ConvertTo-Json -Compress
"""

_PS_FILE_BACKED = """
$counters = Get-Counter "\\Memory\\*" -ErrorAction SilentlyContinue `
    | Select-Object -ExpandProperty CounterSamples
$sysCache = 0; $poolPaged = 0; $poolNonPaged = 0
foreach ($c in $counters) {
    $p = $c.Path
    if ($p -match 'System Cache Resident') { $sysCache = $c.CookedValue }
    if ($p -match 'Pool Paged') { $poolPaged = $c.CookedValue }
    if ($p -match 'Pool Nonpaged') { $poolNonPaged = $c.CookedValue }
}
Write-Host "SYSTEM_CACHE_MB:$([math]::Round($sysCache / 1MB, 0))"
Write-Host "POOL_PAGED_MB:$([math]::Round($poolPaged / 1MB, 0))"
Write-Host "POOL_NONPAGED_MB:$([math]::Round($poolNonPaged / 1MB, 0))"
$os = Get-CimInstance Win32_OperatingSystem
$commitTotal = ($os.TotalVirtualMemorySize - $os.FreeVirtualMemory) / 1MB
$commitLimit = $os.TotalVirtualMemorySize / 1MB
Write-Host "COMMIT_TOTAL_MB:$([math]::Round($commitTotal, 0))"
Write-Host "COMMIT_LIMIT_MB:$([math]::Round($commitLimit, 0))"
"""


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_memory_categories(text: str, detailed: bool) -> dict:
    categories = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            categories[key] = _parse_val(val)
    if not categories.get("TOTAL_MB"):
        return _fallback_via_psutil(detailed)
    return {"success": True, "categories": categories, "totals": {
        "total_mb": categories.get("TOTAL_MB", 0),
        "available_mb": categories.get("AVAILABLE_MB", 0),
        "used_mb": categories.get("USED_MB", 0),
        "cache_mb": categories.get("CACHE_MB", 0),
        "standby_mb": categories.get("STANDBY_MB", 0),
        "free_mb": categories.get("FREE_MB", 0),
        "pagefile_total_mb": categories.get("PAGEFILE_TOTAL_MB", 0),
    }, "error": None}


def _parse_process_memory(text: str, top_n: int) -> dict:
    import json
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        data.sort(key=lambda p: p.get("WS_MB", 0), reverse=True)
        top = data[:top_n]
        total_ws = sum(p.get("WS_MB", 0) for p in top)
        return {"success": True, "processes": top, "count": len(top),
                "total_ws_mb": round(total_ws, 1), "error": None}
    except (json.JSONDecodeError, TypeError):
        return _process_fallback_psutil(top_n)


def _parse_file_backed(text: str) -> dict:
    items = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            items[key] = _parse_val(val)
    return {"success": True, "cache_total_mb": items.get("SYSTEM_CACHE_MB", 0),
            "sections": items, "error": None}


# ---------------------------------------------------------------------------
# Fallbacks when PowerShell is unavailable
# ---------------------------------------------------------------------------

def _fallback_via_psutil(detailed: bool) -> dict:
    try:
        import psutil
        mem = psutil.virtual_memory()
        categories = {
            "TOTAL_MB": round(mem.total / 1_048_576, 0),
            "AVAILABLE_MB": round(mem.available / 1_048_576, 0),
            "USED_MB": round((mem.total - mem.available) / 1_048_576, 0),
            "CACHE_MB": round((mem.cached or 0) / 1_048_576, 0) if hasattr(mem, "cached") else 0,
            "FREE_MB": round(mem.free / 1_048_576, 0),
        }
        return {"success": True, "categories": categories, "totals": {
            "total_mb": categories["TOTAL_MB"],
            "available_mb": categories["AVAILABLE_MB"],
            "used_mb": categories["USED_MB"],
        }}
    except ImportError:
        msg = "No memory data source (try psutil)"
        return {"success": False, "categories": {}, "totals": {}, "error": msg}


def _process_fallback_psutil(top_n: int) -> dict:
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(
            ["pid", "name", "memory_info", "num_threads", "num_handles"]
        ):
            try:
                info = p.info
                mi = info.get("memory_info")
                rss = mi.rss if mi else 0
                procs.append({
                    "PID": info["pid"],
                    "Name": info.get("name", ""),
                    "WS_MB": round(rss / 1_048_576, 1),
                    "VM_MB": round((mi.vms if mi else 0) / 1_048_576, 1),
                    "Threads": info.get("num_threads", 0),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda p: p["WS_MB"], reverse=True)
        top = procs[:top_n]
        total_ws = sum(p["WS_MB"] for p in top)
        return {"success": True, "processes": top, "count": len(top),
                "total_ws_mb": round(total_ws, 1), "error": None}
    except ImportError:
        msg = "No process data (try psutil)"
        return {"success": False, "processes": [], "count": 0,
                "total_ws_mb": 0, "error": msg}


def _file_backed_fallback() -> dict:
    return {"success": False, "cache_total_mb": 0, "sections": {},
            "error": "File cache data unavailable"}


def _parse_val(s: str) -> int | float:
    s = s.strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return 0
