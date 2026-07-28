"""pslist -- process list with CPU, thread, and handle counts. Fixed-width table."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="pslist")
    def list_processes(
        include_kernel: Annotated[bool, Field(default=False, description="Also show kernel processes (-k)")] = False,
        tree: Annotated[bool, Field(default=False, description="Show process tree (-t)")] = False,
    ) -> dict:
        """List processes with PID, CPU time, thread count, and handle count.

        Wraps Sysinternals Pslist.

        ## Return Format
        {"success": bool, "processes": list[dict], "count": int, "error": str | None}
        """
        args = ["-nobanner"]
        if include_kernel:
            args.append("-k")
        if tree:
            args.append("-t")

        proc = manager.run("pslist", args, timeout=15)
        if proc.returncode != 0:
            return {"success": False, "processes": [], "count": 0, "error": proc.stderr.strip()}

        return _parse_pslist(proc.stdout)

    @app.tool(name="pslist_detail")
    def pslist_by_name(
        name: Annotated[str, Field(description="Process name to filter (e.g. explorer")],
    ) -> dict:
        """List details for processes matching a name.

        ## Return Format
        {"success": bool, "processes": list[dict], "count": int}
        """
        proc = manager.run("pslist", ["-nobanner", name], timeout=15)
        if proc.returncode != 0:
            return {"success": False, "processes": [], "count": 0, "error": proc.stderr.strip()}
        return _parse_pslist(proc.stdout)


def _parse_pslist(text: str) -> dict:
    """Parse fixed-width pslist table."""
    lines = text.splitlines()
    processes = []
    header_found = False
    for line in lines:
        if "Name" in line and "Pid" in line and "Thd" in line:
            header_found = True
            continue
        if not header_found or not line.strip() or line.startswith("-"):
            continue
        # Fixed-width columns: Name, Pid, Pri, Thd, Hnd, VM, WS, Priv, CPU Time, Elapsed Time
        parts = line.rsplit(None, 9)
        if len(parts) >= 8:
            try:
                name = parts[0]
                pid = int(parts[1])
                pri = int(parts[2]) if parts[2].isdigit() else 0
                thd = int(parts[3])
                hnd = int(parts[4])
                vm_str = parts[5]
                ws_str = parts[6]
                priv_str = parts[7]
                cpu_time = parts[8] if len(parts) > 8 else ""
                elapsed = parts[9] if len(parts) > 9 else ""
                processes.append(
                    {
                        "name": name,
                        "pid": pid,
                        "priority": pri,
                        "threads": thd,
                        "handles": hnd,
                        "vm_kb": vm_str,
                        "ws_kb": ws_str,
                        "priv_kb": priv_str,
                        "cpu_time": cpu_time,
                        "elapsed": elapsed,
                    }
                )
            except (ValueError, IndexError):
                pass
    return {"success": True, "processes": processes, "count": len(processes), "error": None}
