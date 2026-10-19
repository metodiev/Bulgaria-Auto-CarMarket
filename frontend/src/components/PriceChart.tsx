import type { PricePoint } from "../api/types";
import { formatPrice } from "../lib/format";

export default function PriceChart({
  points,
  currency,
}: {
  points: PricePoint[];
  currency?: string | null;
}) {
  if (points.length < 2) {
    return (
      <div className="grid h-44 place-items-center rounded-xl border border-dashed border-edge text-sm text-slate-500">
        Няма достатъчно ценови промени за графика.
      </div>
    );
  }

  const width = 640;
  const height = 190;
  const padding = 28;
  const prices = points.map((point) => point.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const span = max - min || 1;
  const stepX = (width - padding * 2) / (points.length - 1);
  const coords = points.map((point, index) => {
    const x = padding + index * stepX;
    const y = height - padding - ((point.price - min) / span) * (height - padding * 2);
    return { x, y, point };
  });
  const line = coords.map((item) => `${item.x},${item.y}`).join(" ");
  const area = `${padding},${height - padding} ${line} ${width - padding},${height - padding}`;

  return (
    <div className="space-y-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-52 w-full overflow-visible">
        <defs>
          <linearGradient id="priceArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((ratio) => {
          const y = padding + ratio * (height - padding * 2);
          return (
            <line
              key={ratio}
              x1={padding}
              x2={width - padding}
              y1={y}
              y2={y}
              stroke="#1d3350"
              strokeDasharray="4 6"
            />
          );
        })}
        <polygon points={area} fill="url(#priceArea)" />
        <polyline points={line} fill="none" stroke="#2dd4bf" strokeWidth="2.5" strokeLinejoin="round" />
        {coords.map((item) => (
          <g key={item.point.observed_at}>
            <circle cx={item.x} cy={item.y} r="4" fill="#07111f" stroke="#2dd4bf" strokeWidth="2" />
            <title>{`${formatPrice(item.point.price, item.point.currency || currency)} · ${new Date(
              item.point.observed_at,
            ).toLocaleDateString("bg-BG")}`}</title>
          </g>
        ))}
        <text x={padding} y={height - 8} fill="#64748b" fontSize="11">
          {new Date(points[0].observed_at).toLocaleDateString("bg-BG")}
        </text>
        <text x={width - padding} y={height - 8} fill="#64748b" fontSize="11" textAnchor="end">
          {new Date(points[points.length - 1].observed_at).toLocaleDateString("bg-BG")}
        </text>
        <text x={padding} y={18} fill="#94a3b8" fontSize="11">
          {formatPrice(max, currency)}
        </text>
        <text x={padding} y={height - padding + 4} fill="#94a3b8" fontSize="11">
          {formatPrice(min, currency)}
        </text>
      </svg>
    </div>
  );
}
