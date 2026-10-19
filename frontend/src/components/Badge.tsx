import type { ReactNode } from "react";

export type BadgeTone = "success" | "warning" | "danger" | "info" | "neutral";

const tones: Record<BadgeTone, string> = {
  success: "bg-emerald-500/10 text-emerald-300 ring-emerald-400/30",
  warning: "bg-amber-500/10 text-amber-300 ring-amber-400/30",
  danger: "bg-rose-500/10 text-rose-300 ring-rose-400/30",
  info: "bg-sky-500/10 text-sky-300 ring-sky-400/30",
  neutral: "bg-slate-500/10 text-slate-300 ring-slate-400/20",
};

export default function Badge({
  tone = "neutral",
  children,
}: {
  tone?: BadgeTone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
