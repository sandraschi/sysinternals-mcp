import { useEffect, useState } from "react";
import { Activity, Cpu, Database, Gauge } from "lucide-react";
import { checkHealth } from "../lib/api";

interface HealthCard {
  label: string;
  value: string;
  icon: typeof Activity;
  testId: string;
}

export default function Dashboard() {
  const [health, setHealth] = useState<{ tool_count: number; uptime: number } | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let delay = 1000;
    const poll = async () => {
      while (!cancelled) {
        const h = await checkHealth();
        if (!cancelled) {
          if (h.success) {
            setHealth({ tool_count: h.tool_count || 17, uptime: h.uptime_seconds || 0 });
            setError(false);
            delay = 5000;
          } else {
            setError(true);
            delay = Math.min(delay * 2, 16000);
          }
        }
        if (!cancelled) await new Promise((r) => setTimeout(r, delay));
      }
    };
    poll();
    return () => { cancelled = true; };
  }, []);

  const cards: HealthCard[] = [
    { label: "Tools", value: health ? String(health.tool_count) : "--", icon: Database, testId: "kpi-tools" },
    { label: "Uptime", value: health ? `${Math.round(health.uptime / 3600)}h` : "--", icon: Gauge, testId: "kpi-uptime" },
    { label: "Processes", value: "--", icon: Cpu, testId: "kpi-processes" },
    { label: "Memory", value: "--", icon: Activity, testId: "kpi-memory" },
  ];

  return (
    <div data-testid="dashboard" className="space-y-6">
      <div className="flex items-center gap-2">
        <Activity className="text-amber-500" size={24} />
        <h1 className="text-xl font-semibold text-zinc-100">Dashboard</h1>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((card) => (
          <div
            key={card.label}
            data-testid={card.testId}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-2"
          >
            <div className="flex items-center gap-2 text-zinc-500 text-sm">
              <card.icon size={16} />
              <span>{card.label}</span>
            </div>
            <div className="text-2xl font-bold text-zinc-100">{card.value}</div>
          </div>
        ))}
      </div>
      {error && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-xl p-4 text-red-400 text-sm">
          Backend unreachable. Ensure sysinternals-mcp is running on port 11074.
        </div>
      )}
    </div>
  );
}
