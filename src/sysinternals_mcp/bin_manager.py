"""Binary downloader, Authenticode verifier, and cache manager for Sysinternals tools.

Downloads binaries from https://live.sysinternals.com/<name>.exe,
verifies Authenticode signature (Microsoft, "Sysinternals"), and caches
them in %%LOCALAPPDATA%%\\sysinternals-mcp\\bin\\.
"""

from __future__ import annotations

import logging
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SYSINTERNALS_URL = "https://live.sysinternals.com"
TOOLS = [
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
]

_EULA_FLAG = "-accepteula"


def _cache_dir() -> Path:
    """Resolve the binary cache directory."""
    env = os.environ.get("SYSINTERNALS_CACHE_DIR")
    if env:
        return Path(env)
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    return Path(local_app_data) / "sysinternals-mcp" / "bin"


class BinaryManager:
    """Manages download, verification, and cached execution of Sysinternals binaries."""

    def __init__(self, cache_dir: str | Path | None = None):
        self._cache = Path(cache_dir) if cache_dir else _cache_dir()
        self._cache.mkdir(parents=True, exist_ok=True)
        self._eula_marker = self._cache / ".eula_accepted"

    # -- public interface --------------------------------------------------------

    def ensure(self, name: str) -> Path:
        """Ensure the binary is cached and verified. Downloads if missing. Returns path."""
        path = self.path(name)
        if path.exists():
            return path
        self._download(name)
        self._verify_signature(path)
        return path

    def path(self, name: str) -> Path:
        """Return the expected cache path for a binary."""
        exe_name = self._exe_name(name)
        return self._cache / exe_name

    def accept_eula(self) -> None:
        """Mark EULA as accepted (writes a marker file)."""
        self._eula_marker.write_text("accepted", encoding="utf-8")

    def eula_accepted(self) -> bool:
        return self._eula_marker.exists()

    def ensure_eula(self) -> list[str]:
        """Return extra args needed for EULA acceptance."""
        return [_EULA_FLAG] if self.eula_accepted() else []

    def scan_cached(self) -> dict[str, Any]:
        """List cached binaries with status."""
        result = {}
        for name in TOOLS:
            path = self.path(name)
            result[name] = {
                "cached": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "path": str(path),
            }
        return result

    def ensure_all(self) -> dict[str, str]:
        """Download and verify all 12 tools. Returns {name: status}."""
        results = {}
        for name in TOOLS:
            try:
                self.ensure(name)
                results[name] = "ok"
            except Exception as e:
                results[name] = f"error: {e}"
        return results

    def run(self, name: str, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a cached binary with args and return the CompletedProcess."""
        binary = self.ensure(name)
        extra = self.ensure_eula()
        full_args = [str(binary), *extra, *args]
        logger.debug("running %s", " ".join(full_args))
        return subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    # -- internal ----------------------------------------------------------------

    def _download(self, name: str) -> Path:
        """Download a binary from live.sysinternals.com."""
        exe_name = self._exe_name(name)
        url = f"{SYSINTERNALS_URL}/{exe_name}"
        dest = self._cache / exe_name
        logger.info("Downloading %s from %s", exe_name, url)
        try:
            urllib.request.urlretrieve(url, dest)  # noqa: S310
        except Exception as e:
            raise RuntimeError(f"Failed to download {url}: {e}") from e
        return dest

    def _verify_signature(self, path: Path) -> None:
        """Verify the Authenticode signature of a downloaded binary."""
        if os.name != "nt":
            logger.warning("Skipping Authenticode verification on non-Windows")
            return
        ps = "powershell"
        result = subprocess.run(
            [
                ps,
                "-NoProfile",
                "-Command",
                f"Get-AuthenticodeSignature '{path}' | Select-Object -ExpandProperty Status",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        status = result.stdout.strip()
        if status != "Valid":
            detail = subprocess.run(
                [
                    ps,
                    "-NoProfile",
                    "-Command",
                    f"(Get-AuthenticodeSignature '{path}').SignerCertificate.Subject",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            subject = detail.stdout.strip()
            if "Microsoft" not in subject or "Sysinternals" not in subject:
                if path.exists():
                    path.unlink()
                raise RuntimeError(
                    f"Authenticode verification failed for {path.name}: status={status}, subject={subject}"
                )
        logger.info("Signature verified for %s", path.name)

    @staticmethod
    def _exe_name(name: str) -> str:
        """Map short tool names to their actual EXE filenames."""
        mapping = {
            "autorunsc": "Autorunsc.exe",
            "handle64": "handle64.exe",
            "pslist": "pslist.exe",
            "listdlls": "listdlls.exe",
            "tcpvcon": "tcpvcon.exe",
            "sigcheck": "sigcheck64.exe",
            "accesschk": "accesschk64.exe",
            "accesschk64": "accesschk64.exe",
            "psloggedon": "PsLoggedon.exe",
            "psfile": "psfile64.exe",
            "psfile64": "psfile64.exe",
            "coreinfo": "Coreinfo.exe",
            "du": "du64.exe",
            "du64": "du64.exe",
            "psinfo": "PsInfo.exe",
        }
        return mapping.get(name, f"{name}.exe")
