import { useMode } from "../contexts/ModeContext";

function ModeToggle() {
  const { mode, toggle } = useMode();
  const isLearn = mode === "learn";

  return (
    <button
      type="button"
      onClick={toggle}
      className="flex items-center gap-3 rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-prism-teal/60"
    >
      <span>Demo</span>
      <span
        className={`relative inline-flex h-6 w-12 items-center rounded-full bg-slate-700 transition ${isLearn ? "bg-prism-teal/60" : "bg-slate-700"}`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white transition ${isLearn ? "translate-x-6" : "translate-x-1"}`}
        />
      </span>
      <span className={isLearn ? "text-prism-teal" : "text-slate-400"}>Learn</span>
    </button>
  );
}

export default ModeToggle;
