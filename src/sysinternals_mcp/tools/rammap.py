"""DIY RAMMap equivalent -- physical memory breakdown via native NT APIs and psutil.

RAMMap is excluded from the standard Sysinternals binary set because it is GUI-only
with no scriptable CLI export. This module provides a high-performance equivalent
using direct Windows Native APIs (ntdll.dll NtQuerySystemInformation with
SystemMemoryListInformation, kernel32 GlobalMemoryStatusEx, psapi GetPerformanceInfo)
and in-process psutil. No external Sysinternals binary required.
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
from ctypes import wintypes
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

logger = logging.getLogger(__name__)

_PWSH = "powershell"

# ---------------------------------------------------------------------------
# Native Windows Structures & Constants
# ---------------------------------------------------------------------------

SYSTEM_MEMORY_LIST_INFORMATION_CLASS = 80  # 0x50

# SYSTEM_MEMORY_LIST_COMMAND constants for NtSetSystemInformation(80, ...)
MEMORY_CAPTURE_ACCESSED_BITS = 0
MEMORY_CAPTURE_AND_RESET_ACCESSED_BITS = 1
MEMORY_EMPTY_WORKING_SETS = 2
MEMORY_FLUSH_MODIFIED_LIST = 3
MEMORY_PURGE_STANDBY_LIST = 4
MEMORY_PURGE_PRIORITY0_LIST = 5

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002


class SYSTEM_MEMORY_LIST_INFORMATION(ctypes.Structure):
    """Accurate x64 struct layout matching winsiderss/phnt (Process Hacker Native API)."""

    _fields_ = [
        ("ZeroPageCount", ctypes.c_size_t),
        ("FreePageCount", ctypes.c_size_t),
        ("ModifiedPageCount", ctypes.c_size_t),
        ("ModifiedNoWritePageCount", ctypes.c_size_t),
        ("BadPageCount", ctypes.c_size_t),
        ("PageCountByPriority", ctypes.c_size_t * 8),
        ("RepurposedPagesByPriority", ctypes.c_size_t * 8),
        ("ModifiedPageCountPageFile", ctypes.c_size_t),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", wintypes.DWORD),
        ("ProcessCount", wintypes.DWORD),
        ("ThreadCount", wintypes.DWORD),
    ]


class LUID(ctypes.Structure):
    _fields_ = [
        ("LowPart", wintypes.DWORD),
        ("HighPart", wintypes.LONG),
    ]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", wintypes.DWORD),
    ]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES * 1),
    ]


def _enable_privilege(privilege_name: str) -> bool:
    """Attempt to enable a Windows token privilege (e.g. SeProfileSingleProcessPrivilege)."""
    if os.name != "nt":
        return False
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(token),
        ):
            return False

        try:
            luid = LUID()
            if not advapi32.LookupPrivilegeValueW(None, privilege_name, ctypes.byref(luid)):
                return False

            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

            res = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)
            err = kernel32.GetLastError()
            return res != 0 and err == 0
        finally:
            kernel32.CloseHandle(token)
    except Exception as e:
        logger.debug(f"Failed to enable privilege {privilege_name}: {e}")
        return False


def _query_nt_memory_list() -> dict | None:
    """Query NT kernel memory lists directly via NtQuerySystemInformation class 80."""
    if os.name != "nt":
        return None

    try:
        ntdll = ctypes.windll.ntdll
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        mem_info = SYSTEM_MEMORY_LIST_INFORMATION()
        ret_len = wintypes.ULONG()

        status = ntdll.NtQuerySystemInformation(
            SYSTEM_MEMORY_LIST_INFORMATION_CLASS,
            ctypes.byref(mem_info),
            ctypes.sizeof(mem_info),
            ctypes.byref(ret_len),
        )
        if status != 0:
            return None

        # Get performance info for page size, cache & kernel memory pools
        perf = PERFORMANCE_INFORMATION()
        perf.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
        has_perf = bool(psapi.GetPerformanceInfo(ctypes.byref(perf), perf.cb))

        page_size = perf.PageSize if has_perf and perf.PageSize else 4096
        mb = 1024 * 1024

        # Get general memory status (page file usage and physical memory)
        mstatus = MEMORYSTATUSEX()
        mstatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        has_status = bool(kernel32.GlobalMemoryStatusEx(ctypes.byref(mstatus)))

        total_phys_mb = round((mstatus.ullTotalPhys / mb), 0) if has_status else round((perf.PhysicalTotal * page_size) / mb, 0)
        avail_phys_mb = round((mstatus.ullAvailPhys / mb), 0) if has_status else round((perf.PhysicalAvailable * page_size) / mb, 0)
        used_phys_mb = max(0, total_phys_mb - avail_phys_mb)

        standby_counts = list(mem_info.PageCountByPriority)
        standby_total_pages = sum(standby_counts)
        standby_total_mb = round((standby_total_pages * page_size) / mb, 0)

        zeroed_mb = round((mem_info.ZeroPageCount * page_size) / mb, 0)
        free_mb = round((mem_info.FreePageCount * page_size) / mb, 0)
        modified_mb = round((mem_info.ModifiedPageCount * page_size) / mb, 0)
        modified_nowrite_mb = round((mem_info.ModifiedNoWritePageCount * page_size) / mb, 0)
        bad_mb = round((mem_info.BadPageCount * page_size) / mb, 0)

        cache_mb = round((perf.SystemCache * page_size) / mb, 0) if has_perf else standby_total_mb
        commit_total_mb = round((perf.CommitTotal * page_size) / mb, 0) if has_perf else 0
        commit_limit_mb = round((perf.CommitLimit * page_size) / mb, 0) if has_perf else 0
        kernel_paged_mb = round((perf.KernelPaged * page_size) / mb, 0) if has_perf else 0
        kernel_nonpaged_mb = round((perf.KernelNonpaged * page_size) / mb, 0) if has_perf else 0

        pf_total_mb = round(mstatus.ullTotalPageFile / mb, 0) if has_status else 0
        pf_avail_mb = round(mstatus.ullAvailPageFile / mb, 0) if has_status else 0
        pf_used_mb = max(0, pf_total_mb - pf_avail_mb)

        categories = {
            "TOTAL_MB": total_phys_mb,
            "AVAILABLE_MB": avail_phys_mb,
            "USED_MB": used_phys_mb,
            "CACHE_MB": cache_mb,
            "STANDBY_MB": standby_total_mb,
            "MODIFIED_MB": modified_mb,
            "MODIFIED_NOWRITE_MB": modified_nowrite_mb,
            "FREE_MB": free_mb,
            "ZEROED_MB": zeroed_mb,
            "BAD_MB": bad_mb,
            "PAGEFILE_TOTAL_MB": pf_total_mb,
            "PAGEFILE_USED_MB": pf_used_mb,
            "COMMIT_TOTAL_MB": commit_total_mb,
            "COMMIT_LIMIT_MB": commit_limit_mb,
            "KERNEL_PAGED_MB": kernel_paged_mb,
            "KERNEL_NONPAGED_MB": kernel_nonpaged_mb,
        }

        standby_priorities_mb = {
            str(pri): round((cnt * page_size) / mb, 1)
            for pri, cnt in enumerate(standby_counts)
        }

        return {
            "categories": categories,
            "totals": {
                "total_mb": total_phys_mb,
                "available_mb": avail_phys_mb,
                "used_mb": used_phys_mb,
                "cache_mb": cache_mb,
                "standby_mb": standby_total_mb,
                "free_mb": free_mb,
                "pagefile_total_mb": pf_total_mb,
            },
            "standby_priorities_mb": standby_priorities_mb,
            "perf": {
                "handles": perf.HandleCount if has_perf else 0,
                "processes": perf.ProcessCount if has_perf else 0,
                "threads": perf.ThreadCount if has_perf else 0,
            },
        }
    except Exception as e:
        logger.debug(f"Native memory list query failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------


def register_tool(app: FastMCP, _manager=None) -> None:

    @app.tool(name="rammap_physical")
    def rammap_physical(
        detailed: Annotated[
            bool,
            Field(default=False, description="Include per-priority standby list (0-7) and kernel pool details"),
        ] = False,
    ) -> dict:
        """Show physical memory usage breakdown by category.

        RAMMap-style view: active, standby (priorities 0-7), modified, modified-no-write,
        zeroed, free, bad page counts, system cache, kernel paged/nonpaged pools, and commit limits.

        Uses direct NT kernel system calls (NtQuerySystemInformation / phnt layout) with
        sub-millisecond execution. Falls back to WMI / psutil if native calls fail.

        ## Return Format
        {"success": bool, "categories": dict, "totals": dict, "standby_priorities_mb": dict | None, "error": str | None}
        """
        # Primary: Direct NT Native API
        native_data = _query_nt_memory_list()
        if native_data:
            res = {
                "success": True,
                "categories": native_data["categories"],
                "totals": native_data["totals"],
                "error": None,
                "method": "ntdll_native",
            }
            if detailed:
                res["standby_priorities_mb"] = native_data["standby_priorities_mb"]
                res["perf_counts"] = native_data["perf"]
            return res

        # Secondary: PowerShell WMI Breakdown
        proc = subprocess.run(
            [_PWSH, "-NoProfile", "-Command", _PS_MEMORY_BREAKDOWN],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if proc.returncode != 0:
            return _fallback_via_psutil(detailed)
        return _parse_memory_categories(proc.stdout, detailed)

    @app.tool(name="rammap_processes")
    def rammap_processes(
        top_n: Annotated[int, Field(default=20, description="Number of top processes to return", ge=1, le=200)] = 20,
    ) -> dict:
        """Show per-process memory usage: working set, private bytes, virtual memory, threads, handles.

        RAMMap-style process list sorted by working set descending.
        Uses in-process psutil for speed (<20ms), falling back to PowerShell Get-Process if needed.

        ## Return Format
        {"success": bool, "processes": list[dict], "count": int, "total_ws_mb": float, "error": str | None}
        """
        return _process_in_process_psutil(top_n)

    @app.tool(name="rammap_file_backed")
    def rammap_file_backed() -> dict:
        """Show file-backed page cache, kernel memory pools, and commit metrics.

        Reports System Cache resident bytes, Paged Pool, Nonpaged Pool, Commit Total,
        and Commit Limit.

        ## Return Format
        {"success": bool, "cache_total_mb": float, "sections": dict, "error": str | None}
        """
        native_data = _query_nt_memory_list()
        if native_data:
            cats = native_data["categories"]
            return {
                "success": True,
                "cache_total_mb": cats.get("CACHE_MB", 0),
                "sections": {
                    "SYSTEM_CACHE_MB": cats.get("CACHE_MB", 0),
                    "POOL_PAGED_MB": cats.get("KERNEL_PAGED_MB", 0),
                    "POOL_NONPAGED_MB": cats.get("KERNEL_NONPAGED_MB", 0),
                    "COMMIT_TOTAL_MB": cats.get("COMMIT_TOTAL_MB", 0),
                    "COMMIT_LIMIT_MB": cats.get("COMMIT_LIMIT_MB", 0),
                    "STANDBY_MB": cats.get("STANDBY_MB", 0),
                    "MODIFIED_MB": cats.get("MODIFIED_MB", 0),
                },
                "error": None,
                "method": "ntdll_native",
            }

        # Fallback to PowerShell
        proc = subprocess.run(
            [_PWSH, "-NoProfile", "-Command", _PS_FILE_BACKED],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if proc.returncode != 0:
            return _file_backed_fallback()
        return _parse_file_backed(proc.stdout)

    @app.tool(name="rammap_empty")
    def rammap_empty(
        target: Annotated[
            Literal["standby", "working_sets", "modified", "priority0"],
            Field(
                default="standby",
                description="Memory target to purge/empty: 'standby' (all standby lists), 'working_sets' (system and process working sets), 'modified' (flush modified pages to disk), or 'priority0' (lowest priority standby list only)",
            ),
        ] = "standby",
    ) -> dict:
        """RAMMap equivalent 'Empty' command: purge standby list or working sets.

        Replicates RAMMap's 'Empty Standby List', 'Empty Working Sets', 'Empty Modified Page List',
        or 'Empty Priority 0 Standby List' using NtSetSystemInformation (SystemMemoryListInformation).

        Note: Requires Administrator privileges (SeProfileSingleProcessPrivilege / SeIncreaseQuotaPrivilege).

        ## Return Format
        {"success": bool, "target": str, "freed_mb": float | None, "error": str | None}
        """
        if os.name != "nt":
            return {"success": False, "target": target, "error": "Supported on Windows only"}

        cmd_map = {
            "standby": MEMORY_PURGE_STANDBY_LIST,
            "working_sets": MEMORY_EMPTY_WORKING_SETS,
            "modified": MEMORY_FLUSH_MODIFIED_LIST,
            "priority0": MEMORY_PURGE_PRIORITY0_LIST,
        }
        cmd_val = cmd_map.get(target, MEMORY_PURGE_STANDBY_LIST)

        # Before stats
        before = _query_nt_memory_list()

        # Try enabling required privileges
        _enable_privilege("SeProfileSingleProcessPrivilege")
        _enable_privilege("SeIncreaseQuotaPrivilege")

        try:
            ntdll = ctypes.windll.ntdll
            command_var = wintypes.ULONG(cmd_val)
            status = ntdll.NtSetSystemInformation(
                SYSTEM_MEMORY_LIST_INFORMATION_CLASS,
                ctypes.byref(command_var),
                ctypes.sizeof(command_var),
            )
            if status == 0:
                after = _query_nt_memory_list()
                freed_mb = None
                if before and after:
                    if target == "standby":
                        freed_mb = max(0.0, before["categories"]["STANDBY_MB"] - after["categories"]["STANDBY_MB"])
                    elif target == "working_sets":
                        freed_mb = max(0.0, before["categories"]["USED_MB"] - after["categories"]["USED_MB"])

                return {
                    "success": True,
                    "target": target,
                    "freed_mb": freed_mb,
                    "message": f"Successfully executed empty command for {target}",
                    "error": None,
                }
            elif status == -1073741727 or status == -1073741790:  # STATUS_PRIVILEGE_NOT_HELD / STATUS_ACCESS_DENIED
                return {
                    "success": False,
                    "target": target,
                    "error": "Administrator privilege required. Restart the MCP server or terminal with 'Run as Administrator' to execute RAMMap empty operations.",
                }
            else:
                return {
                    "success": False,
                    "target": target,
                    "error": f"NtSetSystemInformation returned NTSTATUS {status:#x}",
                }
        except Exception as e:
            return {"success": False, "target": target, "error": str(e)}

    @app.tool(name="rammap_summary")
    def rammap_summary() -> dict:
        """Combined memory diagnostic: physical breakdown + top processes + file cache.

        One-shot equivalent of calling rammap_physical, rammap_processes (top 10),
        and rammap_file_backed.

        ## Return Format
        {"success": bool, "physical": dict, "top_processes": list[dict], "file_cache": dict}
        """
        phys = rammap_physical(detailed=True)
        procs = rammap_processes(top_n=10)
        files = rammap_file_backed()
        return {
            "success": True,
            "physical": phys.get("categories", {}) or phys.get("totals", {}),
            "standby_priorities_mb": phys.get("standby_priorities_mb"),
            "top_processes": procs.get("processes", []),
            "file_cache": files.get("cache_total_mb", 0),
            "method": phys.get("method", "wmi_fallback"),
            "error": phys.get("error") or procs.get("error") or files.get("error"),
        }


# ---------------------------------------------------------------------------
# Fast in-process psutil process enumeration
# ---------------------------------------------------------------------------


def _process_in_process_psutil(top_n: int) -> dict:
    try:
        import psutil

        procs = []
        mb = 1024 * 1024
        for p in psutil.process_iter(["pid", "name", "memory_info", "num_threads"]):
            try:
                info = p.info
                mi = info.get("memory_info")
                if not mi:
                    continue
                rss = mi.rss
                procs.append(
                    {
                        "PID": info["pid"],
                        "Name": info.get("name", ""),
                        "WS_MB": round(rss / mb, 1),
                        "Private_MB": round(getattr(mi, "private", rss) / mb, 1),
                        "VM_MB": round(getattr(mi, "vms", 0) / mb, 1),
                        "Threads": info.get("num_threads", 0),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x["WS_MB"], reverse=True)
        top = procs[:top_n]
        total_ws = sum(p["WS_MB"] for p in top)
        return {
            "success": True,
            "processes": top,
            "count": len(top),
            "total_ws_mb": round(total_ws, 1),
            "error": None,
        }
    except Exception as e:
        logger.debug(f"psutil process enumeration error: {e}")
        return _process_fallback_powershell(top_n)


def _process_fallback_powershell(top_n: int) -> dict:
    proc = subprocess.run(
        [_PWSH, "-NoProfile", "-Command", _PS_PROCESS_MEMORY],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if proc.returncode != 0:
        return {"success": False, "processes": [], "count": 0, "total_ws_mb": 0, "error": "Process listing failed"}
    return _parse_process_memory(proc.stdout, top_n)


# ---------------------------------------------------------------------------
# Fallback PowerShell scripts
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
# Parsers & Fallbacks
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
    return {
        "success": True,
        "categories": categories,
        "totals": {
            "total_mb": categories.get("TOTAL_MB", 0),
            "available_mb": categories.get("AVAILABLE_MB", 0),
            "used_mb": categories.get("USED_MB", 0),
            "cache_mb": categories.get("CACHE_MB", 0),
            "standby_mb": categories.get("STANDBY_MB", 0),
            "free_mb": categories.get("FREE_MB", 0),
            "pagefile_total_mb": categories.get("PAGEFILE_TOTAL_MB", 0),
        },
        "standby_priorities_mb": None,
        "error": None,
        "method": "wmi_powershell",
    }


def _parse_process_memory(text: str, top_n: int) -> dict:
    import json

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        data.sort(key=lambda p: p.get("WS_MB", 0), reverse=True)
        top = data[:top_n]
        total_ws = sum(p.get("WS_MB", 0) for p in top)
        return {"success": True, "processes": top, "count": len(top), "total_ws_mb": round(total_ws, 1), "error": None}
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "processes": [], "count": 0, "total_ws_mb": 0, "error": "JSON parse error"}


def _parse_file_backed(text: str) -> dict:
    items = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            items[key] = _parse_val(val)
    return {
        "success": True,
        "cache_total_mb": items.get("SYSTEM_CACHE_MB", 0),
        "sections": items,
        "error": None,
        "method": "wmi_powershell",
    }


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
        return {
            "success": True,
            "categories": categories,
            "totals": {
                "total_mb": categories["TOTAL_MB"],
                "available_mb": categories["AVAILABLE_MB"],
                "used_mb": categories["USED_MB"],
            },
            "standby_priorities_mb": None,
            "error": None,
            "method": "psutil_fallback",
        }
    except ImportError:
        msg = "No memory data source available"
        return {"success": False, "categories": {}, "totals": {}, "standby_priorities_mb": None, "error": msg}


def _file_backed_fallback() -> dict:
    return {"success": False, "cache_total_mb": 0, "sections": {}, "error": "File cache data unavailable"}


def _parse_val(s: str) -> int | float:
    s = s.strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return 0
