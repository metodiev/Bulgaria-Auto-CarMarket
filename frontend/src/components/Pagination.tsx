import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (pages <= 1) {
    return <p className="text-xs text-slate-500">Общо {total} резултата</p>;
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-xs text-slate-500">
        Страница {page} от {pages} · общо {total}
      </p>
      <div className="flex items-center gap-2">
        <button
          className="btn-ghost px-2.5 py-1.5"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Предишна страница"
        >
          <ChevronLeft size={16} />
        </button>
        <button
          className="btn-ghost px-2.5 py-1.5"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          aria-label="Следваща страница"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
