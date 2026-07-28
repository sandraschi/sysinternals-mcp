"""listdlls -- loaded DLLs per process. Multi-section text output."""

from __future__ import annotations

import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="listdlls")
    def list_all_dlls(
        verified: Annotated[bool, Field(default=False, description="Only show verified DLLs (-v)")] = False,
    ) -> dict:
        """List all loaded DLLs across all processes with version info.

        Wraps Sysinternals ListDLLs.

        ## Return Format
        {"success": bool, "processes": list[dict], "count": int, "error": str | None}
        """
        args = ["-nobanner"]
        if verified:
            args.append("-v")

        proc = manager.run("listdlls", args, timeout=30)
        if proc.returncode != 0:
            return {"success": False, "processes": [], "count": 0, "error": proc.stderr.strip()}

        return _parse_listdlls(proc.stdout)

    @app.tool(name="listdlls_by_pid")
    def list_dlls_by_pid(
        pid: Annotated[int, Field(description="Process ID to inspect")],
    ) -> dict:
        """List loaded DLLs for a specific process by PID.

        ## Return Format
        {"success": bool, "dlls": list[dict], "count": int}
        """
        proc = manager.run("listdlls", ["-nobanner", "-r", str(pid)], timeout=15)
        return _parse_listdlls(proc.stdout)


def _parse_listdlls(text: str) -> dict:
    """Parse listdlls multi-section output."""
    lines = text.splitlines()
    processes = []
    current_proc = None
    current_dlls = []

    for line in lines:
        if not line.strip():
            continue
        if ":" in line and "base" not in line.lower():
            # New process section
            if current_proc:
                processes.append({"process": current_proc, "dlls": current_dlls, "dll_count": len(current_dlls)})
            current_dlls = []
            current_proc = line.strip()
            continue
        if current_proc and line.strip():
            # DLL entry: 0x<base> 0x<size> <name> <version>
            m = re.match(r"\s*(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(.+?)(?:\s+(\S+))?$", line)
            if m:
                current_dlls.append(
                    {
                        "base": m.group(1),
                        "size": m.group(2),
                        "name": m.group(3).strip(),
                        "version": m.group(4) if m.group(4) else "",
                    }
                )

    if current_proc and current_dlls:
        processes.append({"process": current_proc, "dlls": current_dlls, "dll_count": len(current_dlls)})

    return {"success": True, "processes": processes, "count": len(processes), "error": None}
