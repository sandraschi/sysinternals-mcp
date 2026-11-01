import { Menu, X, Activity, Cpu, HardDrive, Network, LayoutDashboard } from "lucide-react";
import { useState } from "react";

const NAV = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { label: "Processes", icon: Cpu, href: "/processes" },
  { label: "Memory", icon: Activity, href: "/memory" },
  { label: "Disk", icon: HardDrive, href: "/disk" },
  { label: "Network", icon: Network, href: "/network" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`${collapsed ? "w-16" : "w-56"} transition-all duration-200 bg-zinc-900 border-r border-zinc-800 flex flex-col`}
    >
      <div className="flex items-center justify-between p-3 border-b border-zinc-800">
        {!collapsed && <span className="text-sm font-semibold text-zinc-100">SysMCP</span>}
        <button onClick={() => setCollapsed(!collapsed)} className="text-zinc-400 hover:text-zinc-100">
          {collapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {NAV.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 text-sm text-zinc-400 rounded-lg hover:bg-zinc-800 hover:text-zinc-100"
          >
            <item.icon size={18} />
            {!collapsed && <span>{item.label}</span>}
          </a>
        ))}
      </nav>
    </aside>
  );
}
