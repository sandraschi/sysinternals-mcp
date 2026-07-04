"""psfile -- remotely opened files on this machine. Line-oriented text."""

from __future__ import annotations

import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="psfile")
    def list_remote_files(
        path_filter: Annotated[
            str | None, Field(default=None, description="Filter by path (optional)")
        ] = None,
        accept_eula: Annotated[
            bool | None, Field(default=None, description="Accept EULA (stored once)")
        ] = None,
    ) -> dict:
        """List files opened by remote systems via network shares.

        Wraps Sysinternals PsFile.

        ## Return Format
        {"success": bool, "files": list[dict], "count": int, "error": str | None}
        """
        if accept_eula:
            manager.accept_eula()

        args = ["-nobanner"]
        if path_filter:
            args.append(path_filter)

        proc = manager.run("psfile", args, timeout=15)
        if proc.returncode != 0:
            return {"success": False, "files": [], "count": 0, "error": proc.stderr.strip()}

        return _parse_psfile(proc.stdout)

    @app.tool(name="psfile_close")
    def close_remote_file(
        file_id: Annotated[int, Field(description="File ID to close")],
    ) -> dict:
        """Close a file opened by a remote system.

        ## Return Format
        {"success": bool, "message": str}
        """
        proc = manager.run("psfile", ["-nobanner", "-c", str(file_id)], timeout=15)
        if proc.returncode == 0:
            return {"success": True, "message": f"File ID {file_id} closed"}
        return {"success": False, "message": proc.stderr.strip() or proc.stdout.strip()}


def _parse_psfile(text: str) -> dict:
    """Parse psfile line-oriented output. Sections start with path, then indented details."""
    lines = text.splitlines()
    files = []
    current_file = None
    file_id_seq = [0]

    path_re = re.compile(r"^(.+?):\s*$")

    for line in lines:
        stripped = line.strip()
        if not stripped or "PsFile" in stripped or "-" * 5 in stripped:
            continue

        m = path_re.match(stripped)
        if m and ":" in stripped and not stripped.startswith(" "):
            if current_file:
                files.append(current_file)
            file_id_seq[0] += 1
            current_file = {"id": file_id_seq[0], "path": m.group(1)}
        elif current_file and stripped:
            # Looks like a detail line
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                current_file[key.strip().lower()] = val.strip()
            else:
                current_file.setdefault("details", []).append(stripped)

    if current_file:
        files.append(current_file)

    return {"success": True, "files": files, "count": len(files), "error": None}
