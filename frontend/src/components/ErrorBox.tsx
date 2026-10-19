import { AlertTriangle, RefreshCw } from "lucide-react";

export default function ErrorBox({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <div className="flex items-center gap-2">
        <AlertTriangle size={18} />
        <span>{message}</span>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost border-rose-400/30 px-3 py-1.5 text-xs text-rose-100">
          <RefreshCw size={14} /> Опитай отново
        </button>
      )}
    </div>
  );
}
