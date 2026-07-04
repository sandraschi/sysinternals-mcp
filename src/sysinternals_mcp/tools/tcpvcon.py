"""tcpvcon -- TCP/UDP connections + owning process (console TCPView). CSV via -c."""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="tcpvcon")
    def list_connections(
        all_states: Annotated[
            bool, Field(default=False, description="Show all states, incl. TIME_WAIT (-a)")
        ] = False,
    ) -> dict:
        """List all TCP/UDP connections with owning process.

        Wraps Sysinternals Tcpvcon with CSV output parsing.

        ## Return Format
        {"success": bool, "connections": list[dict], "count": int, "error": str | None}
        """
        args = ["-c", "-nobanner"]
        if all_states:
            args.append("-a")

        proc = manager.run("tcpvcon", args, timeout=15)
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            if stderr:
                return {"success": False, "connections": [], "count": 0, "error": stderr}

        return _parse_csv(proc.stdout)


def _parse_csv(text: str) -> dict:
    """Parse CSV from tcpvcon output."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        conns = [row for row in reader]
        return {"success": True, "connections": conns, "count": len(conns), "error": None}
    except Exception as e:
        return {"success": False, "connections": [], "count": 0, "error": str(e)}
