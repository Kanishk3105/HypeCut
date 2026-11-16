import type { ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  phase: string;
}

export function EmptyState({ icon, title, description, phase }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-line bg-surface-900/60 px-8 py-14 text-center">
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-surface-800 text-zinc-500">
        {icon}
      </span>
      <h2 className="text-base font-medium text-zinc-100">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-zinc-500">{description}</p>
      <span className="mt-5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-[11px] font-medium text-accent-400">
        {phase}
      </span>
    </div>
  );
}
