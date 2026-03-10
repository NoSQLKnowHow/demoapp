import { ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { useMode } from "../contexts/ModeContext";
import { useAuth } from "../contexts/AuthContext";
import ModeToggle from "./ModeToggle";
import SectionTabs from "./SectionTabs";

function LayoutShell({ children }: { children: ReactNode }) {
  const { mode } = useMode();
  const { logout } = useAuth();
  const location = useLocation();

  const isLearn = mode === "learn";

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-prism-teal">Prism</p>
            <h1 className="text-lg font-semibold text-slate-100">Unified Data Projections</h1>
          </div>
          <div className="flex items-center gap-4">
            <ModeToggle />
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
        {isLearn ? (
          <div className="bg-prism-teal/10 py-2 text-center text-xs text-prism-teal">
            Learn Mode active — showing SQL, explain plans, and pipeline details.
          </div>
        ) : null}
        <SectionTabs activePath={location.pathname} />
      </header>
      <main className="mx-auto w-full max-w-6xl px-6 py-8 text-slate-100">
        {children}
      </main>
    </div>
  );
}

export default LayoutShell;
