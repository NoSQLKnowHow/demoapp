import { ReactNode } from "react";

import { useMode } from "../contexts/ModeContext";
import type { ResponseMeta } from "../lib/types";

type LearnPanelProps = {
  meta?: ResponseMeta | null;
  title?: string;
  children?: ReactNode;
};

function LearnPanel({ meta, title = "Behind the scenes", children }: LearnPanelProps) {
  const { mode } = useMode();
  const isLearn = mode === "learn";

  if (!isLearn) {
    return null;
  }

  const hasSql = Boolean(meta?.sql);
  const hasContent = Boolean(children);

  if (!hasSql && !hasContent) {
    return null;
  }

  return (
    <aside className="mt-6 space-y-4 rounded-xl border border-prism-teal/30 bg-prism-teal/5 p-5 text-sm text-prism-teal">
      <div className="flex items-center gap-2 text-prism-teal">
        <span className="text-xs uppercase tracking-[0.25em]">Learn Mode</span>
        {meta?.execution_time_ms !== undefined ? (
          <span className="text-prism-teal/70">· {meta.execution_time_ms?.toFixed(2)} ms</span>
        ) : null}
        {meta?.operation_id ? <span className="text-prism-teal/70">· {meta.operation_id}</span> : null}
      </div>
      <h3 className="text-base font-semibold text-slate-100">{title}</h3>
      {hasSql ? (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-prism-teal/70">SQL</p>
          <pre className="overflow-x-auto rounded-lg bg-slate-950/70 p-4 text-xs text-slate-200">
            <code>{meta?.sql}</code>
          </pre>
        </div>
      ) : null}
      {children}
    </aside>
  );
}

export default LearnPanel;
