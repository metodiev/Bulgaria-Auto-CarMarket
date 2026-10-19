import { Loader2 } from "lucide-react";

export default function Loading({ label = "Зареждане…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-400">
      <Loader2 className="animate-spin text-accent" size={20} />
      {label}
    </div>
  );
}
