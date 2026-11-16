import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-line bg-surface-900 p-5 shadow-[0_1px_0_rgba(255,255,255,0.02)_inset] ${className}`}
    >
      {children}
    </div>
  );
}
