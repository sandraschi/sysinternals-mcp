"""psinfo -- system info summary: OS, uptime, hotfixes, services. Labeled sections."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="psinfo")
    def system_info(
        show_hotfixes: Annotated[
            bool, Field(default=False, description="Show installed hotfixes (-h)")
        ] = False,
        show_services: Annotated[
            bool, Field(default=False, description="Show running services (-s)")
        ] = False,
    ) -> dict:
        """Show detailed system information: OS version, uptime, hotfixes, services.

        Wraps Sysinternals PsInfo.

        ## Return Format
        {"success": bool, "sections": dict, "raw": str, "error": str | None}
        """
        args = ["-nobanner"]
        if show_hotfixes:
            args.append("-h")
        if show_services:
            args.append("-s")

        proc = manager.run("psinfo", args, timeout=15)
        if proc.returncode != 0:
            return {"success": False, "sections": {}, "raw": proc.stdout.strip(), "error": proc.stderr.strip()}

        return _parse_psinfo(proc.stdout)

    @app.tool(name="psinfo_remote")
    def system_info_remote(
        server: Annotated[str, Field(description="Remote computer name")],
    ) -> dict:
        """Show system info for a remote computer.

        ## Return Format
        {"success": bool, "sections": dict, "raw": str}
        """
        proc = manager.run("psinfo", ["-nobanner", "\\\\" + server], timeout=15)
        return _parse_psinfo(proc.stdout)


def _parse_psinfo(text: str) -> dict:
    """Parse psinfo sectioned output. Each section has key: value lines."""
    lines = text.splitlines()
    sections = {}
    current_section = "system"

    for line in lines:
        stripped = line.strip()
        if not stripped or "PsInfo" in stripped:
            continue

        # Section header: all-caps line ending with colon
        if stripped.isupper() and stripped.endswith(":"):
            current_section = stripped.rstrip(":").lower().replace(" ", "_")
            sections.setdefault(current_section, {})
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            section = sections.setdefault(current_section, {})
            section[key.strip()] = val.strip()
        else:
            sections.setdefault(current_section, {})
            sections[current_section].setdefault("_lines", []).append(stripped)

    return {"success": True, "sections": sections, "raw": text.strip(), "error": None}
