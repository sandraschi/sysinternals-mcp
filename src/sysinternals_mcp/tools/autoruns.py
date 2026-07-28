"""autorunsc -- startup/persistence scan. Native CSV via -c flag."""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="autorunsc")
    def run_autorunsc(
        accept_eula: Annotated[bool | None, Field(default=None, description="Accept EULA (stored once)")] = None,
        hashes: Annotated[bool, Field(default=False, description="Include SHA-1 hashes (-h)")] = False,
        verify: Annotated[bool, Field(default=False, description="Verify digital signatures (-v)")] = False,
        all_users: Annotated[bool, Field(default=False, description="Check all user accounts (-a *)")] = False,
    ) -> dict:
        """Scan startup programs, scheduled tasks, services, drivers, and browser extensions.

        Wraps Sysinternals Autorunsc with CSV output parsing.

        ## Return Format
        {"success": bool, "entries": list[dict], "count": int, "error": str | None}
        """
        if accept_eula:
            manager.accept_eula()

        args = ["-c", "-nobanner"]
        if hashes:
            args.append("-h")
        if verify:
            args.append("-v")
        if all_users:
            args.append("-a")
            args.append("*")
        else:
            args.append("-a")
            args.append("s")  # default: services only

        proc = manager.run("autorunsc", args, timeout=60)
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            if stderr:
                return {"success": False, "entries": [], "count": 0, "error": stderr}

        return _parse_csv(proc.stdout)

    @app.tool(name="autorunsc_schedule")
    def run_autorunsc_schedule(
        accept_eula: Annotated[bool | None, Field(default=None, description="Accept EULA (stored once)")] = None,
        hashes: Annotated[bool, Field(default=False, description="Include SHA-1 hashes (-h)")] = False,
    ) -> dict:
        """Scan only scheduled tasks autoruns (fast subset).

        ## Return Format
        {"success": bool, "entries": list[dict], "count": int}
        """
        if accept_eula:
            manager.accept_eula()

        args = ["-c", "-nobanner", "-a", "s"]
        if hashes:
            args.append("-h")

        proc = manager.run("autorunsc", args, timeout=30)
        return _parse_csv(proc.stdout)


def _parse_csv(text: str) -> dict:
    """Parse CSV from autorunsc output."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        entries = [row for row in reader]
        return {"success": True, "entries": entries, "count": len(entries), "error": None}
    except Exception as e:
        return {"success": False, "entries": [], "count": 0, "error": str(e)}
