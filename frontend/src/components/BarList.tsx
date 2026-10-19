import type { StatBucket } from "../api/types";
import { formatNumber, formatPrice } from "../lib/format";

export default function BarList({
  title,
  buckets,
  valueLabel = "обяви",
}: {
  title: string;
  buckets: StatBucket[];
  valueLabel?: string;
}) {
  const max = Math.max(...buckets.map((bucket) => bucket.count), 1);
  return (
    <div className="card p-4">
      <h2 className="mb-3 text-sm font-semibold text-white">{title}</h2>
      {buckets.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-500">Няма данни.</p>
      ) : (
        <div className="space-y-2.5">
          {buckets.map((bucket) => (
            <div key={bucket.key}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="truncate text-slate-300">{bucket.key}</span>
                <span className="shrink-0 text-slate-500">
                  {formatNumber(bucket.count)} {valueLabel}
                  {bucket.avg_price !== null ? ` · ${formatPrice(bucket.avg_price)}` : ""}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-ink">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent/70 to-accent"
                  style={{ width: `${Math.max(4, (bucket.count / max) * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
