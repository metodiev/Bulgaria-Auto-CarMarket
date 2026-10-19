import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, formatApiError } from "../api/client";
import type { Page, ScraperError, Source } from "../api/types";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import { formatDate } from "../lib/format";

export default function Errors() {
  const [data, setData] = useState<Page<ScraperError> | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run") ?? "";

  useEffect(() => {
    api<Source[]>("/sources").then(setSources).catch(() => setSources([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const query = new URLSearchParams({ page: String(page), page_size: "50" });
    if (sourceId) query.set("source_id", sourceId);
    if (runId) query.set("run_id", runId);
    api<Page<ScraperError>>(`/errors?${query.toString()}`)
      .then(setData)
      .catch((err) => setError(formatApiError(err)))
      .finally(() => setLoading(false));
  }, [page, sourceId, runId, reloadKey]);

  const sourceName = (id: string) => sources.find((source) => source.id === id)?.name ?? id.slice(0, 8);

  return (
    <div className="space-y-5">
      {error && (
        <ErrorBox message={error} onRetry={() => setReloadKey((value) => value + 1)} />
      )}

      <section className="card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px]">
            <label className="label">Източник</label>
            <select
              className="input"
              value={sourceId}
              onChange={(event) => {
                setSourceId(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Всички</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>
          <p className="pb-2 text-xs text-slate-500">
            Показани са последните {data?.total ?? 0} записа за грешки.
            {runId && <> · филтър за run {runId.slice(0, 8)}</>}
          </p>
        </div>
      </section>

      {loading ? (
        <Loading label="Зареждане на грешките…" />
      ) : (
        <section className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/50 bg-ink/40">
                <tr>
                  <th className="table-head px-4 py-3">Време</th>
                  <th className="table-head px-4 py-3">Източник</th>
                  <th className="table-head px-4 py-3">Тип</th>
                  <th className="table-head px-4 py-3">Съобщение</th>
                  <th className="table-head px-4 py-3">URL</th>
                  <th className="table-head px-4 py-3">Run</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((item) => (
                  <tr key={item.id} className="border-b border-edge/30 last:border-0">
                    <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500">
                      {formatDate(item.occurred_at)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-300">{sourceName(item.source_id)}</td>
                    <td className="px-4 py-2.5 text-rose-300">{item.error_type}</td>
                    <td className="max-w-[480px] px-4 py-2.5 text-slate-300">{item.message}</td>
                    <td className="max-w-[260px] truncate px-4 py-2.5 text-xs text-slate-500">
                      {item.url ? (
                        <a href={item.url} target="_blank" rel="noreferrer" className="hover:text-accent">
                          {item.url}
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <Link to={`/scrape-runs`} className="text-xs font-semibold text-accent hover:underline">
                        {item.run_id.slice(0, 8)}
                      </Link>
                    </td>
                  </tr>
                ))}
                {data && data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-sm text-slate-500">
                      Няма записани грешки.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
