"""FastMCP 3.4 server exposing 12 Sysinternals CLI tools."""

import logging
import os
import sys

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


def main():
    """Server entry point -- dual transport (stdio or HTTP)."""
    port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
    if port:
        import uvicorn
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        sys.argv = ["sysinternals-mcp", "--mode", "http", "--host", host, "--port", str(port)]
        uvicorn.run(app.sse_app(), host=host, port=int(port), log_level="info")
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
