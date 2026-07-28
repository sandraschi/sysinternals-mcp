"""psloggedon -- logged-on users, local + via network. Fixed-width table."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="psloggedon")
    def list_logged_on_users(
        local: Annotated[bool, Field(default=True, description="Show locally logged-on users")] = True,
        network: Annotated[
            bool, Field(default=False, description="Show network logons from this machine (-x)")
        ] = False,
    ) -> dict:
        """List users logged on locally and optionally via network connections.

        Wraps Sysinternals PsLoggedon.

        ## Return Format
        {"success": bool, "users": list[dict], "count": int, "error": str | None}
        """
        args = ["-nobanner", "-l"] if local else ["-nobanner"]
        if network:
            args.append("-x")

        proc = manager.run("psloggedon", args, timeout=15)
        if proc.returncode != 0:
            return {"success": False, "users": [], "count": 0, "error": proc.stderr.strip()}

        return _parse_psloggedon(proc.stdout)

    @app.tool(name="psloggedon_server")
    def list_logged_on_remote(
        server: Annotated[str, Field(description="Remote server name to check")],
    ) -> dict:
        """List users logged on to a remote server.

        ## Return Format
        {"success": bool, "users": list[dict], "count": int}
        """
        proc = manager.run("psloggedon", ["-nobanner", "\\\\" + server], timeout=15)
        return _parse_psloggedon(proc.stdout)


def _parse_psloggedon(text: str) -> dict:
    """Parse psloggedon fixed-width table output."""
    lines = text.splitlines()
    users = []
    in_users = False
    for line in lines:
        stripped = line.strip()
        if "Users" in stripped and "logged" in stripped:
            in_users = True
            continue
        if in_users and stripped:
            # Format: <user> <type> <sessions>
            parts = stripped.split(None, 3)
            if len(parts) >= 2:
                users.append(
                    {
                        "user": parts[0],
                        "type": parts[1] if len(parts) > 1 else "",
                        "detail": " ".join(parts[2:]) if len(parts) > 2 else "",
                    }
                )
    return {"success": True, "users": users, "count": len(users), "error": None}
