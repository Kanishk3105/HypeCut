import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { navItems } from "./navItems";
import { Scissors } from "lucide-react";
import type { ReactNode } from "react";

export function NavLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex w-full flex-col border-b border-line bg-surface-900 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-500/15 text-accent-400">
            <Scissors size={18} aria-hidden />
          </span>
          <div>
            <p className="text-sm font-semibold tracking-wide text-zinc-100">HypeCut Local</p>
            <p className="text-[11px] text-zinc-500">Local AI clipping studio</p>
          </div>
        </div>
        <nav
          aria-label="Primary"
          className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-5"
        >
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                [
                  "relative flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "text-zinc-50"
                    : "text-zinc-400 hover:bg-surface-800 hover:text-zinc-200",
                ].join(" ")
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-md bg-surface-700 ring-1 ring-accent-500/40"
                      transition={{ type: "spring", stiffness: 380, damping: 32 }}
                    />
                  )}
                  <span className="relative flex items-center gap-2.5">
                    <item.icon size={16} aria-hidden />
                    {item.label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto hidden border-t border-line px-5 py-3 md:block">
          <p className="text-[11px] text-zinc-600">₹0 · runs 100% on this PC</p>
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-6 py-8 md:px-10">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  );
}
