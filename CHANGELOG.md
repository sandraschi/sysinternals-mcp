# Changelog

## [0.1.0] - 2026-08-17

### Added
- Initial release -- v0.1.0
- All 12 Sysinternals CLI tools: autorunsc, handle64, pslist, listdlls, tcpvcon, sigcheck, accesschk, psloggedon, psfile, coreinfo, du, psinfo
- BinaryManager: first-run download from live.sysinternals.com, Authenticode verification, caching, EULA acceptance
- Per-tool parsers for CSV (autorunsc, sigcheck, tcpvcon) and fixed-width/text output (remaining 8 tools)
- Dual transport: stdio (IDE) and HTTP (port 11074)
- Fleet scaffold: pyproject.toml, justfile, ruff, pytest, manifest.json
