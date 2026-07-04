"""sigcheck -- Authenticode verification, version info, VT lookup. Native CSV via -c."""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="sigcheck")
    def run_sigcheck(
        path: Annotated[str, Field(description="File or directory path to scan")],
        recursive: Annotated[
            bool, Field(default=False, description="Scan subdirectories recursively (-s)")
        ] = False,
        virus_total: Annotated[
            bool, Field(default=False, description="Look up SHA-256 on VirusTotal (-v)")
        ] = False,
        accept_eula: Annotated[
            bool | None, Field(default=None, description="Accept EULA (stored once)")
        ] = None,
    ) -> dict:
        """Verify file digital signatures, version info, and optionally check VirusTotal.

        Wraps Sysinternals Sigcheck with CSV output parsing.

        ## Return Format
        {"success": bool, "files": list[dict], "count": int, "error": str | None}
        """
        if accept_eula:
            manager.accept_eula()

        args = ["-c", "-nobanner", "-q"]
        if recursive:
            args.append("-s")
        if virus_total:
            args.append("-v")
        args.append(path)

        proc = manager.run("sigcheck", args, timeout=60)
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            if stderr:
                return {"success": False, "files": [], "count": 0, "error": stderr}

        return _parse_csv(proc.stdout)


def _parse_csv(text: str) -> dict:
    """Parse CSV from sigcheck output."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        files = [row for row in reader]
        return {"success": True, "files": files, "count": len(files), "error": None}
    except Exception as e:
        return {"success": False, "files": [], "count": 0, "error": str(e)}
