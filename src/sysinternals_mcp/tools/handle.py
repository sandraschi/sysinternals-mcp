"""handle64 -- open handles / file locks. CSV-ish via -v flag."""

from __future__ import annotations

import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="handle64")
    def list_handles(
        pattern: Annotated[
            str | None, Field(default=None, description="Filter handles by name/pattern")
        ] = None,
        verbose: Annotated[
            bool, Field(default=False, description="Verbose output with handle counts (-v)")
        ] = False,
    ) -> dict:
        """List open handles and file locks on the system.

        Wraps Sysinternals Handle64.

        ## Return Format
        {"success": bool, "handles": list[dict], "count": int, "error": str | None}
        """
        args = ["-nobanner"]
        if verbose:
            args.append("-v")
        if pattern:
            args.append(pattern)

        proc = manager.run("handle64", args, timeout=30)
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            if stderr:
                return {"success": False, "handles": [], "count": 0, "error": stderr}

        return _parse_handle_text(proc.stdout)

    @app.tool(name="handle64_by_pid")
    def list_handles_by_pid(
        pid: Annotated[int, Field(description="Process ID to enumerate handles for")],
    ) -> dict:
        """List open handles for a specific process by PID.

        ## Return Format
        {"success": bool, "handles": list[dict], "count": int}
        """
        proc = manager.run("handle64", ["-nobanner", "-p", str(pid)], timeout=15)
        return _parse_handle_text(proc.stdout)


def _parse_handle_text(text: str) -> dict:
    """Parse handle64 output -- pid:name -> lines after header."""
    lines = text.splitlines()
    handles = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Handle v") or "-" * 10 in line:
            continue
        # Format: <pid>: <name>  <type>  <handle>
        m = re.match(r"(\d+):\s+(.+?)\s{2,}(\w+)\s{2,}(\d+)", line)
        if m:
            handles.append({
                "pid": int(m.group(1)),
                "name": m.group(2).strip(),
                "type": m.group(3),
                "handle": m.group(4),
            })
    return {"success": True, "handles": handles, "count": len(handles), "error": None}
