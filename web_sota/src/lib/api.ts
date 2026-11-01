const BASE = "/api/v1";

export interface HealthResponse {
  success: boolean;
  status?: string;
  server?: string;
  server_name?: string;
  version?: string;
  uptime_seconds?: number;
  tool_count?: number;
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    // Relative so Vite dev proxy (and any port reclaim) keeps working.
    const r = await fetch(`/health`);
    if (!r.ok) return { success: false };
    return { success: true, ...(await r.json()) };
  } catch {
    return { success: false };
  }
}

export interface ToolInfo {
  id: string;
  exe: string | null;
  description: string;
  reversible: boolean;
  cached: boolean;
  size: number;
  path: string | null;
}

export interface ReverseResult {
  success: boolean;
  tool?: string;
  binary?: string;
  size?: number;
  run_id?: string | null;
  gym_url?: string | null;
  gym_frontend?: string;
  error?: string;
  hint?: string;
}

export async function listTools(): Promise<ToolInfo[]> {
  const d = await apiGet<{ success: boolean; tools: ToolInfo[] }>(`/tools`);
  return d.tools;
}

export async function reverseTool(tool: string): Promise<ReverseResult> {
  return apiPost<ReverseResult>(`/reverse`, { tool });
}

export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`API ${r.status}: ${r.statusText}`);
  return r.json();
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`API ${r.status}: ${r.statusText}`);
  return r.json();
}
