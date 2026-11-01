import { useEffect, useState } from "react";
import { Wrench, FlaskConical, ExternalLink } from "lucide-react";
import { listTools, reverseTool, type ToolInfo } from "../lib/api";

export default function Tools() {
  const [tools, setTools] = useState<ToolInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    listTools()
      .then((t) => {
        if (!cancelled) setTools(t);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onReverse = async (id: string) => {
    setBusy(id);
    try {
      const r = await reverseTool(id);
      setResult((prev) => ({
        ...prev,
        [id]: r.success
          ? `Gym run ${r.run_id} started for ${r.binary}`
          : `Failed: ${r.error ?? "unknown"}${r.hint ? ` - ${r.hint}` : ""}`,
      }));
    } catch (e) {
      setResult((prev) => ({
        ...prev,
        [id]: `Failed: ${e instanceof Error ? e.message : String(e)}`,
      }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div data-testid="tools" className="space-y-6">
      <div className="flex items-center gap-2">
        <Wrench className="text-amber-500" size={24} />
        <h1 className="text-xl font-semibold text-zinc-100">Binaries</h1>
        <span className="text-xs text-zinc-500">each reversible into the reversing-mcp gym inbox</span>
      </div>
      {error && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-xl p-4 text-red-400 text-sm">
          Backend unreachable. Ensure sysinternals-mcp is running. ({error})
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(tools ?? []).map((t) => (
          <div
            key={t.id}
            data-testid={`tool-${t.id}`}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm text-zinc-100">{t.exe ?? t.id}</span>
              <span className="text-xs text-zinc-500">
                {t.cached ? `${Math.round(t.size / 1024)} KB` : "not cached"}
              </span>
            </div>
            <p className="text-xs text-zinc-400">{t.description}</p>
            {t.path && <p className="text-[11px] font-mono text-zinc-600 truncate">{t.path}</p>}
            <div className="flex items-center gap-2 pt-1">
              <button
                data-testid={`reverse-${t.id}`}
                disabled={!t.reversible || busy === t.id}
                onClick={() => onReverse(t.id)}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <FlaskConical size={14} />
                {busy === t.id ? "Sending..." : "Reverse"}
              </button>
              <a
                href="http://127.0.0.1:10751/gym"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-200"
              >
                <ExternalLink size={12} /> gym inbox
              </a>
            </div>
            {result[t.id] && <p className="text-xs text-zinc-400">{result[t.id]}</p>}
            {!t.reversible && (
              <p className="text-[11px] text-zinc-600">built-in, no binary to reverse</p>
            )}
          </div>
        ))}
      </div>
      {tools === null && !error && <p className="text-sm text-zinc-500">Loading binaries...</p>}
    </div>
  );
}
