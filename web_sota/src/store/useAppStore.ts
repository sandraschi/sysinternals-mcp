import { create } from "zustand";

interface ProcessEntry {
  Name: string;
  PID: number;
  WS_MB: number;
  Private_MB?: number;
  VM_MB?: number;
}

interface AppState {
  backendOk: boolean | null;
  processes: ProcessEntry[];
  backendDot: "green" | "red" | "gray";
  setBackendOk: (ok: boolean) => void;
  setProcesses: (p: ProcessEntry[]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  backendOk: null,
  processes: [],
  backendDot: "gray",
  setBackendOk: (ok: boolean) =>
    set({ backendOk: ok, backendDot: ok ? "green" : "red" }),
  setProcesses: (p: ProcessEntry[]) => set({ processes: p }),
}));
