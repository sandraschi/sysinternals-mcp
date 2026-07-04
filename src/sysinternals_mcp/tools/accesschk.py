"""accesschk -- effective permissions on files, registry keys, and services. Text output."""

from __future__ import annotations

import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="accesschk")
    def check_permissions(
        path: Annotated[str, Field(description="File, directory, registry path, or service name")],
        target: Annotated[
            str | None,
            Field(default=None, description="User or group to check (omit for effective access)")
        ] = None,
        recursive: Annotated[
            bool, Field(default=False, description="Recurse subdirectories (-s)")
        ] = False,
        accept_eula: Annotated[
            bool | None, Field(default=None, description="Accept EULA (stored once)")
        ] = None,
    ) -> dict:
        """Check effective permissions on files, directories, registry keys, or services.

        Wraps Sysinternals AccessChk.

        ## Return Format
        {"success": bool, "entries": list[dict], "count": int, "error": str | None}
        """
        if accept_eula:
            manager.accept_eula()

        args = ["-nobanner"]
        if recursive:
            args.append("-s")
        if target:
            args.append(target)
        args.append(path)

        proc = manager.run("accesschk", args, timeout=30)
        if proc.returncode != 0:
            return {"success": False, "entries": [], "count": 0, "error": proc.stderr.strip()}

        return _parse_accesschk(proc.stdout)

    @app.tool(name="accesschk_service")
    def check_service_permissions(
        service_name: Annotated[str, Field(description="Service name to check")],
    ) -> dict:
        """Check effective permissions on a specific Windows service.

        ## Return Format
        {"success": bool, "entries": list[dict], "count": int}
        """
        proc = manager.run("accesschk", ["-nobanner", "-c", service_name], timeout=15)
        if proc.returncode == 0:
            return _parse_accesschk(proc.stdout)
        return {"success": True, "entries": [{"raw": proc.stdout.strip()}], "count": 1, "error": None}


def _parse_accesschk(text: str) -> dict:
    """Parse accesschk line-oriented output. Lines start with access rights."""
    lines = text.splitlines()
    entries = []
    for line in lines:
        stripped = line.strip()
        if not stripped or "AccessChk" in stripped or "-" * 5 in stripped:
            continue
        # Format: <right> <path> or RW <path>
        m = re.match(r"^[ \t]*([RW ]+)?\s+(.+)$", stripped)
        if m:
            entries.append({"access": (m.group(1) or "").strip(), "path": m.group(2).strip()})
        else:
            entries.append({"raw": stripped})
    return {"success": True, "entries": entries, "count": len(entries), "error": None}
