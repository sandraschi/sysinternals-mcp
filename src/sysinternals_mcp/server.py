"""FastMCP 3.4 server exposing 12 Sysinternals CLI tools."""

import asyncio
import json
import logging
import os
import sys
import time as _time
import urllib.request

if os.name == "nt":
    try:
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except (ImportError, OSError, AttributeError):
        pass

logging.basicConfig(level=logging.WARNING)
for name in ["mcp.server.lowlevel.server", "fastmcp"]:
    logging.getLogger(name).setLevel(logging.WARNING)

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from sysinternals_mcp.bin_manager import BinaryManager
from sysinternals_mcp.tools.accesschk import register_tool as reg_accesschk
from sysinternals_mcp.tools.autoruns import register_tool as reg_autoruns
from sysinternals_mcp.tools.coreinfo import register_tool as reg_coreinfo
from sysinternals_mcp.tools.du import register_tool as reg_du
from sysinternals_mcp.tools.handle import register_tool as reg_handle
from sysinternals_mcp.tools.listdlls import register_tool as reg_listdlls
from sysinternals_mcp.tools.psfile import register_tool as reg_psfile
from sysinternals_mcp.tools.psinfo import register_tool as reg_psinfo
from sysinternals_mcp.tools.pslist import register_tool as reg_pslist
from sysinternals_mcp.tools.psloggedon import register_tool as reg_psloggedon
from sysinternals_mcp.tools.rammap import register_tool as reg_rammap
from sysinternals_mcp.tools.sigcheck import register_tool as reg_sigcheck
from sysinternals_mcp.tools.tcpvcon import register_tool as reg_tcpvcon
from sysinternals_mcp.tools.treemap import register_tool as reg_treemap

app = FastMCP(
    "Sysinternals MCP",
    instructions="""# Sysinternals MCP [v0.1.0]
FastMCP 3.4 wrapper for 12 Sysinternals CLI tools -- all confirmed CLI-native,
no GUI automation required. First-run auto-downloads binaries from
https://live.sysinternals.com/ and verifies Authenticode signatures.

Binary cache: %%LOCALAPPDATA%%\\sysinternals-mcp\\bin\\
EULA accepted once; stored in cache directory.

## Tools
- autorunsc  -- startup/persistence scan
- handle64   -- open handles/file locks
- pslist     -- process list with CPU/thread/handle counts
- listdlls   -- loaded DLLs per process
- tcpvcon    -- TCP/UDP connections + owning process
- sigcheck   -- Authenticode verification, version, VT lookup
- accesschk  -- effective permissions on file/registry/service
- psloggedon -- logged-on users
- psfile     -- remotely opened files
- coreinfo   -- CPU topology, NUMA, cache, feature flags
- du         -- directory size breakdown
- rammap     -- physical memory breakdown (DIY RAMMap via WMI, no binary)
- treemap    -- interactive memory treemap HTML (WizTree-style, D3.js)
- psinfo     -- system info (OS, uptime, hotfixes, services)
    """,
    version="0.1.0",
)

_manager = BinaryManager()

_START_TIME = _time.time()

TOOL_DESCRIPTIONS = {
    "autorunsc": "Startup/persistence scan (Autorunsc.exe)",
    "handle64": "Open handles / file locks (handle64.exe)",
    "pslist": "Process list with CPU/thread/handle counts (pslist.exe)",
    "listdlls": "Loaded DLLs per process (listdlls.exe)",
    "tcpvcon": "TCP/UDP connections + owning process (tcpvcon.exe)",
    "sigcheck": "Authenticode verification, version, VT lookup (sigcheck64.exe)",
    "accesschk": "Effective permissions on file/registry/service (accesschk64.exe)",
    "accesschk64": "Effective permissions on file/registry/service (accesschk64.exe)",
    "psloggedon": "Logged-on users (PsLoggedon.exe)",
    "psfile": "Remotely opened files (psfile64.exe)",
    "psfile64": "Remotely opened files (psfile64.exe)",
    "coreinfo": "CPU topology, NUMA, cache, feature flags (Coreinfo.exe)",
    "du": "Directory size breakdown (du64.exe)",
    "du64": "Directory size breakdown (du64.exe)",
    "psinfo": "System info - OS, uptime, hotfixes, services (PsInfo.exe)",
    "rammap": "Physical memory breakdown via WMI - built-in, no binary",
    "treemap": "Interactive memory treemap HTML - built-in, no binary",
}

# Canonical short IDs for the /api/v1/tools listing: 12 cached EXEs
# plus 2 built-ins (rammap/treemap) that have no binary to reverse.
TOOL_IDS = [
    "autorunsc",
    "handle64",
    "pslist",
    "listdlls",
    "tcpvcon",
    "sigcheck",
    "accesschk64",
    "psloggedon",
    "psfile64",
    "coreinfo",
    "du64",
    "psinfo",
    "rammap",
    "treemap",
]

_NO_BINARY = {"rammap", "treemap"}


def _tool_count() -> int:
    try:
        mgr = getattr(app, "_tool_manager", None)
        tools = getattr(mgr, "tools", None) if mgr is not None else None
        if isinstance(tools, dict):
            return len(tools)
    except Exception:
        pass
    return len(TOOL_IDS)


def _health_payload() -> dict:
    return {
        "status": "healthy",
        "success": True,
        "server": "sysinternals-mcp",
        "server_name": "sysinternals-mcp",
        "version": "0.1.0",
        "uptime_seconds": int(_time.time() - _START_TIME),
        "tool_count": _tool_count(),
    }


@app.custom_route("/health", methods=["GET"])
@app.custom_route("/api/health", methods=["GET"])
@app.custom_route("/api/v1/health", methods=["GET"])
async def _health(_request: Request) -> JSONResponse:
    return JSONResponse(_health_payload())


@app.custom_route("/api/v1/tools", methods=["GET"])
async def _api_tools(_request: Request) -> JSONResponse:
    items = []
    try:
        cached = await asyncio.to_thread(_manager.scan_cached)
    except Exception:
        cached = {}
    for tid in TOOL_IDS:
        if tid in _NO_BINARY:
            items.append(
                {
                    "id": tid,
                    "exe": None,
                    "description": TOOL_DESCRIPTIONS.get(tid, tid),
                    "reversible": False,
                    "cached": True,
                    "size": 0,
                    "path": None,
                }
            )
            continue
        info = cached.get(tid, {}) if isinstance(cached, dict) else {}
        try:
            exe = _manager._exe_name(tid)
        except Exception:
            exe = f"{tid}.exe"
        items.append(
            {
                "id": tid,
                "exe": exe,
                "description": TOOL_DESCRIPTIONS.get(tid, tid),
                "reversible": True,
                "cached": bool(info.get("cached", False)),
                "size": int(info.get("size", 0) or 0),
                "path": info.get("path"),
            }
        )
    return JSONResponse({"success": True, "tools": items, "count": len(items)})


@app.custom_route("/api/v1/reverse", methods=["POST"])
async def _api_reverse(request: Request) -> JSONResponse:
    """Send a cached Sysinternals binary to the reversing-mcp gym inbox.

    Body: {"tool": "pslist"} (short id, with or without .exe).
    Effect: ensure() the binary locally, then POST the absolute path to
    REVERSING_MCP_URL/api/v1/gym/runs so both servers share the same host FS.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON body"}, status_code=400)
    raw = str((body or {}).get("tool", "")).strip().lower()
    if raw.endswith(".exe"):
        raw = raw[:-4]
    # Normalise 32/64 aliases to the cached id.
    aliases = {
        "accesschk": "accesschk64",
        "psfile": "psfile64",
        "du": "du64",
        "sigcheck": "sigcheck",
        "handle": "handle64",
    }
    tool = aliases.get(raw, raw)
    if tool in _NO_BINARY:
        return JSONResponse(
            {"success": False, "error": f"'{raw}' is a built-in (no binary to reverse)"},
            status_code=400,
        )
    if tool not in TOOL_IDS:
        return JSONResponse(
            {"success": False, "error": f"Unknown tool '{raw}'", "known_tools": TOOL_IDS},
            status_code=404,
        )
    try:
        path = await asyncio.to_thread(_manager.ensure, tool)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Download/verify failed: {e}"}, status_code=502)
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    reversing_base = os.environ.get("REVERSING_MCP_URL", "http://127.0.0.1:10750").rstrip("/")
    payload = json.dumps(
        {"target": str(path), "test_files": [], "notes": f"sysinternals-mcp reverse {tool}"}
    ).encode()
    req = urllib.request.Request(
        f"{reversing_base}/api/v1/gym/runs",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = await asyncio.to_thread(urllib.request.urlopen, req, None, 15)
        data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "tool": tool,
                "binary": str(path),
                "size": size,
                "error": f"reversing-mcp unreachable at {reversing_base}: {e}",
                "hint": "Start reversing-mcp backend (port 10750), then retry",
            },
            status_code=502,
        )
    run_id = data.get("run_id") if isinstance(data, dict) else None
    return JSONResponse(
        {
            "success": bool(run_id),
            "tool": tool,
            "binary": str(path),
            "size": size,
            "run_id": run_id,
            "gym_url": f"{reversing_base}/api/v1/gym/runs/{run_id}" if run_id else None,
            "gym_frontend": "http://127.0.0.1:10751/gym",
            "raw": data,
        }
    )


def main():
    """Server entry point -- dual transport (stdio or HTTP)."""
    port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
    if port:
        import uvicorn

        host = os.environ.get("MCP_HOST", "127.0.0.1")
        sys.argv = ["sysinternals-mcp", "--mode", "http", "--host", host, "--port", str(port)]
        uvicorn.run(app.http_app(), host=host, port=int(port), log_level="info")
    else:
        app.run(transport="stdio")


def register_tools():
    """Register all 12 tool suites with the MCP server."""
    reg_autoruns(app, _manager)
    reg_handle(app, _manager)
    reg_pslist(app, _manager)
    reg_listdlls(app, _manager)
    reg_tcpvcon(app, _manager)
    reg_sigcheck(app, _manager)
    reg_accesschk(app, _manager)
    reg_psloggedon(app, _manager)
    reg_psfile(app, _manager)
    reg_coreinfo(app, _manager)
    reg_du(app, _manager)
    reg_psinfo(app, _manager)
    reg_rammap(app, _manager)
    reg_treemap(app, _manager)


register_tools()

if __name__ == "__main__":
    main()
