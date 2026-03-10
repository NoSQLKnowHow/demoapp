import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

type Mode = "demo" | "learn";

type ModeContextValue = {
  mode: Mode;
  setMode: (mode: Mode) => void;
  toggle: () => void;
};

const STORAGE_KEY = "prism-mode";

const ModeContext = createContext<ModeContextValue | undefined>(undefined);

const loadInitialMode = (): Mode => {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "learn" ? "learn" : "demo";
};

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<Mode>(loadInitialMode);

  const value = useMemo<ModeContextValue>(() => ({
    mode,
    setMode: (next: Mode) => {
      setModeState(next);
      localStorage.setItem(STORAGE_KEY, next);
    },
    toggle: () => {
      setModeState((prev) => {
        const next = prev === "demo" ? "learn" : "demo";
        localStorage.setItem(STORAGE_KEY, next);
        return next;
      });
    },
  }), [mode]);

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export function useMode() {
  const ctx = useContext(ModeContext);
  if (!ctx) {
    throw new Error("useMode must be used within ModeProvider");
  }
  return ctx;
}
