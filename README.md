# Sysinternals MCP

> **FastMCP 3.4 wrapper for 12 Sysinternals CLI tools** -- autorunsc, handle64, pslist, listdlls, tcpvcon, sigcheck, accesschk, psloggedon, psfile, coreinfo, du, psinfo.

**Stack:** Python 3.12+ -- FastMCP 3.4.2 -- uv -- ruff

All 12 tools are confirmed CLI-native. No GUI automation, no fake backends.
First-run auto-downloads each binary from `https://live.sysinternals.com/`,
verifies the Authenticode signature, and caches it.

## Tools

| Tool | Function | What it does |
|------|----------|-------------|
| `autorunsc` | `run_autorunsc()` | Startup/persistence scan -- CSV output via `-c` |
| `handle64` | `list_handles()` | Open handles/file locks -- verbose via `-v` |
| `pslist` | `list_processes()` | Process list with CPU, thread, handle counts |
| `listdlls` | `list_all_dlls()` | Loaded DLLs per process with version info |
| `tcpvcon` | `list_connections()` | TCP/UDP connections + owning process |
| `sigcheck` | `run_sigcheck()` | Authenticode verification, version, VT lookup |
| `accesschk` | `check_permissions()` | Effective permissions on files/registry/services |
| `psloggedon` | `list_logged_on_users()` | Logged-on users, local + network |
| `psfile` | `list_remote_files()` | Remotely opened files on this machine |
| `coreinfo` | `get_cpu_info()` | CPU topology, NUMA, cache, feature flags |
| `du` | `disk_usage()` | Directory size breakdown (recursive) |
| `psinfo` | `system_info()` | System info: OS, uptime, hotfixes, services |

## Quick start

```powershell
git clone https://github.com/sandraschi/sysinternals-mcp.git
cd sysinternals-mcp
uv sync --group dev
uv run sysinternals-mcp    # stdio MCP for IDE
```

First run auto-downloads binaries and stores them in `%LOCALAPPDATA%\sysinternals-mcp\bin\`.

## Transport

| Mode | Command |
|------|---------|
| stdio | `uv run sysinternals-mcp` |
| HTTP | `MCP_PORT=11074 uv run sysinternals-mcp` |

## Binary handling

- **No EXEs committed to git.** Binaries downloaded on first use from live.sysinternals.com.
- **Authenticode verification:** rejects anything not signed by Microsoft / Sysinternals.
- **EULA:** accepted once per machine (marker file in cache dir).

## Excluded tools (GUI-only, no scriptable export)

- RAMMap -- no CLI export flag exists.
- Process Explorer -- GUI-only, no scriptable CLI output.

## License

MIT
