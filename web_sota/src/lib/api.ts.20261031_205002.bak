const BASE = "/api/v1";

export interface HealthResponse {
  success: boolean;
  server?: string;
  version?: string;
  uptime_seconds?: number;
  tool_count?: number;
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const r = await fetch(`http://127.0.0.1:11074/health`);
    if (!r.ok) return { success: false };
    return { success: true, ...(await r.json()) };
  } catch {
    return { success: false };
  }
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
