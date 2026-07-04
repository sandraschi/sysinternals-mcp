"""Self-contained D3 treemap HTML generator for memory data (WizTree-style view)."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

_TREEMAP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Memory Treemap</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #09090b; color: #e4e4e7; font-family: system-ui, sans-serif; padding: 16px; }
h1 { font-size: 18px; margin-bottom: 8px; color: #f4f4f5; }
#chart { width: 100%; height: calc(100vh - 120px); }
.tooltip {
  position: absolute; background: #18181b; border: 1px solid #27272a; color: #e4e4e7;
  padding: 8px 12px; border-radius: 6px; font-size: 13px; pointer-events: none; display: none;
  z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.legend { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; font-size: 12px; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-swatch { width: 10px; height: 10px; border-radius: 2px; }
.stats { display: flex; gap: 16px; font-size: 13px; color: #a1a1aa; margin-bottom: 8px; }
rect { stroke: #09090b; stroke-width: 1; }
rect:hover { stroke: #f59e0b; stroke-width: 2; }
</style>
</head>
<body>
<div class="stats">
  <span>Total: <strong id="totalMb">--</strong> MB</span>
  <span>Processes: <strong id="procCount">--</strong></span>
</div>
<div class="legend" id="legend"></div>
<div id="chart"></div>
<div class="tooltip" id="tooltip"></div>
<script>
const DATA = %DATA%;

const colorMap = {
  'system': '#3b82f6', 'browser': '#f59e0b', 'dev': '#22c55e',
  'media': '#ec4899', 'office': '#8b5cf6', 'game': '#ef4444',
  'service': '#06b6d4', 'other': '#71717a',
};

function categorize(name) {
  n = name.toLowerCase();
  if (['system', 'idle', 'registry', 'smss', 'csrss', 'wininit', 'lsass', 'services',
      'svchost', 'winlogon', 'spoolsv', 'conhost'].some(x => n.includes(x))) return 'system';
  if (['chrome', 'firefox', 'edge', 'brave', 'opera', 'msedge', 'iexplore'].some(x => n.includes(x))) return 'browser';
  if (['python', 'node', 'code', 'cursor', 'nvim', 'vim', 'powershell', 'pwsh',
      'terminal', 'wt', 'windbg', 'cmake', 'git', 'ssh', 'docker'].some(x => n.includes(x))) return 'dev';
  if (['spotify', 'vlc', 'wmplayer', 'music', 'obs', 'audacity',
       'photos', 'mpv'].some(x => n.includes(x))) return 'media';
  if (['outlook', 'excel', 'word', 'powerpoint', 'onenote', 'teams'].some(x => n.includes(x))) return 'office';
  if (['steam', 'blizzard', 'epic', 'battle', 'game', 'unity', 'unreal'].some(x => n.includes(x))) return 'game';
  if (['svchost', 'runtimebroker', 'sihost', 'taskhost', 'background',
       'widgets', 'searchapp', 'security', 'defender', 'smartscreen',
       'shellexperience', 'startmenuexperience', 'textinput'].some(x => n.includes(x))) return 'service';
  return 'other';
}

const root = { name: 'Memory', children: DATA.map(d => ({
  name: d.Name, value: d.WS_MB * 1024 * 1024,
  category: categorize(d.Name),
  pid: d.PID,
  private: d.Private_MB || 0,
  vm: d.VM_MB || 0,
})) };

const width = document.getElementById('chart').clientWidth;
const height = window.innerHeight - 160;

const treemap = d3.treemap().size([width, height]).paddingOuter(2).paddingInner(1).round(true);
const hier = d3.hierarchy(root).sum(d => d.value).sort((a, b) => b.value - a.value);
treemap(hier);

const svg = d3.select('#chart').append('svg').attr('width', width).attr('height', height);
const tooltip = d3.select('#tooltip');
const totalMb = DATA.reduce((s, d) => s + d.WS_MB, 0);
document.getElementById('totalMb').textContent = totalMb.toFixed(0);
document.getElementById('procCount').textContent = DATA.length;

const cats = [...new Set(DATA.map(d => categorize(d.Name)))];
const leg = d3.select('#legend');
cats.forEach(c => { leg.append('span').attr('class', 'legend-item')
  .html(`<span class="legend-swatch" style="background:${colorMap[c]||colorMap.other}"></span> ${c}`); });

const leaf = svg.selectAll('g').data(hier.leaves()).join('g').attr('transform', d => `translate(${d.x0},${d.y0})`);
leaf.append('rect')
  .attr('width', d => d.x1 - d.x0).attr('height', d => d.y1 - d.y0)
  .attr('fill', d => colorMap[d.data.category] || colorMap.other)
  .attr('opacity', d => Math.min(1, 0.5 + (d.data.value / hier.value) * 2))
  .on('mouseover', (e, d) => {
    tooltip.style('display', 'block')
      .html(`<strong>${d.data.name}</strong> (PID ${d.data.pid})<br>
             WS: ${(d.data.value/1048576).toFixed(1)} MB<br>
             Private: ${d.data.private.toFixed(1)} MB<br>`)
      .style('left', (e.pageX+12)+'px').style('top', (e.pageY-10)+'px');
  }).on('mousemove', (e) => tooltip.style('left', (e.pageX+12)+'px').style('top', (e.pageY-10)+'px'))
  .on('mouseout', () => tooltip.style('display', 'none'));

leaf.append('text').attr('font-size', d => Math.min(11, Math.max(7, (d.x1-d.x0) / 10)))
  .attr('x', 3).attr('y', 14).attr('fill', '#fff').style('text-shadow', '0 1px 2px #000')
  .text(d => d.x1-d.x0 > 40 ? d.data.name : '')
  .append('tspan').attr('x', 3).attr('dy', 13).attr('fill', '#a1a1aa')
  .text(d => d.x1-d.x0 > 50 ? `${(d.data.value/1048576).toFixed(0)} MB` : '');
</script>
</body>
</html>"""


def register_tool(app: FastMCP, _manager=None) -> None:

    @app.tool(name="rammap_treemap")
    def rammap_treemap(
        top_n: Annotated[
            int, Field(default=60, description="Number of top processes to include in treemap", ge=5, le=200)
        ] = 60,
        min_ws_mb: Annotated[
            float, Field(default=1.0, description="Minimum working set in MB to include", ge=0)
        ] = 1.0,
    ) -> dict:
        """Generate a WizTree-style interactive treemap of process memory usage.

        Creates a self-contained HTML file with an embedded D3.js squarified treemap,
        colored by process category (system, browser, dev, media, etc.) with hover
        tooltips showing PID, working set, and private bytes.

        The HTML is fully self-contained (loads D3 from CDN) and opens in any browser.

        ## Return Format
        {"success": bool, "file_path": str, "processes": int, "total_mb": float}

        ## Examples
            rammap_treemap(top_n=100, min_ws_mb=0.5)
        """
        # Collect memory data from PowerShell
        _pwsh = "powershell"
        proc = subprocess.run(
            [
                _pwsh, "-NoProfile", "-Command",
                r"Get-Process | Where-Object { $_.Id -gt 0 } | Sort-Object WorkingSet64 -Descending "
                r"| Select-Object -First 200 @{N='Name';E={$_.ProcessName}}, "
                r"@{N='WS_MB';E={[math]::Round($_.WorkingSet64 / 1MB, 1)}}, "
                r"@{N='PID';E={$_.Id}}, "
                r"@{N='Private_MB';E={[math]::Round($_.PrivateMemorySize64 / 1MB, 1)}}, "
                r"@{N='VM_MB';E={[math]::Round($_.VirtualMemorySize64 / 1MB, 1)}} "
                r"| ConvertTo-Json -Compress",
            ],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        if proc.returncode != 0:
            return _fallback_psutil(top_n, min_ws_mb)

        return _generate_treemap(proc.stdout, top_n, min_ws_mb)


def _generate_treemap(json_text: str, top_n: int, min_ws_mb: float) -> dict:
    import json as _json
    try:
        data = _json.loads(json_text)
        if isinstance(data, dict):
            data = [data]
    except (_json.JSONDecodeError, TypeError):
        return _fallback_psutil(top_n, min_ws_mb)

    # Filter and sort
    data = [d for d in data if d.get("WS_MB", 0) >= min_ws_mb]
    data.sort(key=lambda d: d.get("WS_MB", 0), reverse=True)
    data = data[:top_n]

    if not data:
        return {"success": False, "file_path": "", "processes": 0, "total_mb": 0,
                "error": "No processes meet the minimum WS_MB threshold"}

    total_mb = sum(d.get("WS_MB", 0) for d in data)

    # Generate HTML
    html = _TREEMAP_HTML.replace("%DATA%", _json.dumps(data, indent=2))

    out_dir = Path(tempfile.gettempdir()) / "sysinternals-mcp"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "memory_treemap.html"
    out_path.write_text(html, encoding="utf-8")

    return {
        "success": True,
        "file_path": str(out_path),
        "processes": len(data),
        "total_mb": round(total_mb, 0),
        "error": None,
    }


def _fallback_psutil(top_n: int, min_ws_mb: float) -> dict:
    try:
        import psutil
        data = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                mi = p.info.get("memory_info")
                ws = (mi.rss if mi else 0) / 1_048_576
                if ws >= min_ws_mb:
                    data.append({
                        "Name": p.info.get("name", ""),
                        "WS_MB": round(ws, 1),
                        "PID": p.info["pid"],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        data.sort(key=lambda d: d["WS_MB"], reverse=True)
        data = data[:top_n]
        import json as _json
        html = _TREEMAP_HTML.replace("%DATA%", _json.dumps(data, indent=2))
        out_dir = Path(tempfile.gettempdir()) / "sysinternals-mcp"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "memory_treemap.html"
        out_path.write_text(html, encoding="utf-8")
        total_mb = sum(d["WS_MB"] for d in data)
        return {"success": True, "file_path": str(out_path), "processes": len(data),
                "total_mb": round(total_mb, 0), "error": None}
    except ImportError:
        return {"success": False, "file_path": "", "processes": 0, "total_mb": 0,
                "error": "No process data source (try psutil)"}
