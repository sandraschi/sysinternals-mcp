import { useAppStore } from "../store/useAppStore";

export default function Topbar() {
  const backendDot = useAppStore((s) => s.backendDot);

  return (
    <header className="h-12 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-4">
      <h1 className="text-sm font-medium text-zinc-200">Sysinternals MCP Dashboard</h1>
      <div className="flex items-center gap-2">
        <span
          className={`inline-block w-2 h-2 rounded-full animate-pulse ${
            backendDot === "green" ? "bg-green-500" : backendDot === "red" ? "bg-red-500" : "bg-zinc-500"
          }`}
        />
        <span className="text-xs text-zinc-500">
          {backendDot === "green" ? "Connected" : backendDot === "red" ? "Offline" : "Connecting..."}
        </span>
      </div>
    </header>
  );
}
