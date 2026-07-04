"""coreinfo -- CPU topology, NUMA, cache, feature flags. Labeled key: value output."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from sysinternals_mcp.bin_manager import BinaryManager


def register_tool(app: FastMCP, manager: BinaryManager) -> None:

    @app.tool(name="coreinfo")
    def get_cpu_info(
        all_features: Annotated[
            bool, Field(default=False, description="Show all feature flags (default shows deltas)")
        ] = False,
    ) -> dict:
        """Show CPU topology, NUMA node layout, cache sizes, and feature flags.

        Wraps Sysinternals Coreinfo.

        ## Return Format
        {"success": bool, "cpu_topology": list[dict], "features": list[dict], "error": str | None}
        """
        args = ["-nobanner"]
        if all_features:
            args.append("-a")

        proc = manager.run("coreinfo", args, timeout=15)
        if proc.returncode != 0:
            return {"success": False, "cpu_topology": [], "features": [], "error": proc.stderr.strip()}

        return _parse_coreinfo(proc.stdout)


def _parse_coreinfo(text: str) -> dict:
    """Parse coreinfo labeled output."""
    lines = text.splitlines()
    topology = []
    features = []

    for line in lines:
        stripped = line.strip()
        if not stripped or "Coreinfo" in stripped:
            continue
        if "AMD" in stripped or "Intel" in stripped or "x86" in stripped or "ARM" in stripped:
            topology.append({"key": "cpu", "value": stripped})
            continue
        if "*" in stripped or " " in stripped[:2]:
            # Feature flag line: * <name> or <tab> <name>
            feature_name = stripped.lstrip("* \t")
            if feature_name and not feature_name.startswith("-"):
                is_enabled = stripped.strip().startswith("*")
                features.append({"name": feature_name, "enabled": is_enabled})
        elif ":" in stripped:
            key, _, val = stripped.partition(":")
            topology.append({"key": key.strip(), "value": val.strip()})

    return {
        "success": True,
        "cpu_topology": topology,
        "features": features,
        "feature_count": len(features),
        "error": None,
    }
