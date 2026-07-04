# Sysinternals MCP -- install

## Prerequisites

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/) for dependency management
- **Windows** -- Sysinternals tools are Windows-native binaries
- Internet access for first-run binary download

## Install

```powershell
git clone https://github.com/sandraschi/sysinternals-mcp.git
cd sysinternals-mcp
uv sync --group dev
```

## IDE config (Cursor)

Add to your Cursor `mcp.json`:

```json
{
  "mcpServers": {
    "sysinternals-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:\\Dev\\repos\\sysinternals-mcp", "sysinternals-mcp"]
    }
  }
}
```

## IDE config (Claude Desktop)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sysinternals-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:\\Dev\\repos\\sysinternals-mcp", "sysinternals-mcp"]
    }
  }
}
```

## HTTP mode

```powershell
$env:MCP_PORT=11074
uv run sysinternals-mcp
```

The server listens on `http://127.0.0.1:11074/mcp` for MCP streamable HTTP.

## EULA

On first run, accept the Sysinternals EULA by setting `accept_eula=true` on any tool call.
The acceptance is cached in the binary directory and persists across restarts.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Binary not found" | First-run download failed | Ensure internet access, check `%LOCALAPPDATA%\sysinternals-mcp\bin\` |
| "Authenticode verification failed" | Downloaded binary tampered | Clear cache dir, re-run |
| "Access denied" running tool | Missing admin rights for some tools (du, accesschk) | Run the host IDE as Administrator |
