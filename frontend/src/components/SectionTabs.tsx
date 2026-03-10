import { NavLink } from "react-router-dom";
import clsx from "clsx";

import { sections } from "../lib/sections";

type SectionTabsProps = {
  activePath: string;
};

function SectionTabs({ activePath }: SectionTabsProps) {
  return (
    <nav className="border-t border-slate-800 bg-slate-900/60">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-6 py-2">
        {sections.map((section) => (
          <NavLink
            key={section.path}
            to={section.path}
            className={({ isActive }) =>
              clsx(
                "rounded-lg px-3 py-2 text-sm transition",
                isActive || activePath.startsWith(section.path)
                  ? "bg-prism-teal/20 text-prism-teal"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50",
              )
            }
          >
            {section.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

export default SectionTabs;
