"""du -- directory size breakdown. Recursive, per-folder, CSV output via -v."""

from __future__ import annotations

import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="du")
    def disk_usage(
        path: Annotated[str, Field(description="Directory path to analyze")],
        n_children: Annotated[
            int | None, Field(default=None, description="Show top N subdirectories by size (-n)")
        ] = None,
        accept_eula: Annotated[bool | None, Field(default=None, description="Accept EULA (stored once)")] = None,
    ) -> dict:
        """Show disk usage for a directory tree, broken down by subdirectory.

        Wraps Sysinternals DU. Uses verbose (-v) output for per-directory breakdown.

        ## Return Format
        {"success": bool, "directories": list[dict], "total": dict, "error": str | None}
        """
        if accept_eula:
            manager.accept_eula()

        args = ["-nobanner", "-v"]
        if n_children is not None:
            args.extend(["-n", str(n_children)])
        args.append(path)

        proc = manager.run("du", args, timeout=120)
        if proc.returncode != 0:
            return {"success": False, "directories": [], "total": {}, "error": proc.stderr.strip()}

        return _parse_du(proc.stdout)

    @app.tool(name="du_quick")
    def disk_usage_quick(
        path: Annotated[str, Field(description="Directory path to analyze")],
    ) -> dict:
        """Quick disk usage summary for a directory (one level, no recursion into children).

        ## Return Format
        {"success": bool, "directories": list[dict], "total": dict}
        """
        proc = manager.run("du", ["-nobanner", "-v", "-n", "0", path], timeout=60)
        return _parse_du(proc.stdout)


def _parse_du(text: str) -> dict:
    """Parse du verbose output. Lines: <bytes> <dirpath>."""
    lines = text.splitlines()
    directories = []
    total = {}

    for line in lines:
        stripped = line.strip()
        if not stripped or "Du" in stripped or "-" * 5 in stripped:
            continue
        # Format: <size_bytes> <path>
        m = re.match(r"^([\d,]+)\s+(.+)$", stripped)
        if m:
            size_str = m.group(1).replace(",", "")
            try:
                directories.append(
                    {
                        "size_bytes": int(size_str),
                        "path": m.group(2).strip(),
                    }
                )
            except ValueError:
                pass
        elif stripped.lower().startswith("total"):
            parts = stripped.split(None, 3)
            if len(parts) >= 2:
                try:
                    total = {"size_bytes": int(parts[1].replace(",", "")), "text": stripped}
                except ValueError:
                    total = {"text": stripped}

    return {
        "success": True,
        "directories": directories,
        "directory_count": len(directories),
        "total": total or {"text": "total not found in output"},
        "error": None,
    }
