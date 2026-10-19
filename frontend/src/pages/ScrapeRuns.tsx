import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Play, RefreshCw, RotateCcw } from "lucide-react";
import { api, formatApiError, getAdminKey } from "../api/client";
import type { Page, ScrapeRun, Source } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import { formatDate, formatNumber, runStatusTone, statusLabel } from "../lib/format";

function duration(run: ScrapeRun): string {
  if (!run.started_at) return "—";
  const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
  const seconds = Math.max(0, Math.round((end - new Date(run.started_at).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export default function ScrapeRuns() {
  const [sources, setSources] = useState<Source[]>([]);
  const [data, setData] = useState<Page<ScrapeRun> | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ScrapeRun | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);
  const [triggerSource, setTriggerSource] = useState("");
  const [maxPages, setMaxPages] = useState("1");
  const [maxListings, setMaxListings] = useState("5");
  const [triggering, setTriggering] = useState(false);

  const load = async (targetPage = page) => {
    setLoading(true);
    setError(null);
    try {
      const [sourceList, runs] = await Promise.all([
        api<Source[]>("/sources"),
        api<Page<ScrapeRun>>(`/scrape-runs?page=${targetPage}&page_size=20`),
      ]);
      setSources(sourceList);
      setData(runs);
      if (!triggerSource && sourceList.length > 0) {
        const verified = sourceList.find((source) => source.enabled && source.status === "verified");
        setTriggerSource(verified?.id ?? "");
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(page);
  }, [page]);

  const active = useMemo(
    () => data?.items.some((run) => run.status === "running" || run.status === "pending") ?? false,
    [data],
  );

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => void load(page), 5000);
    return () => window.clearInterval(timer);
  }, [active, page]);

  const sourceName = (sourceId: string) =>
    sources.find((source) => source.id === sourceId)?.name ?? sourceId.slice(0, 8);

  const trigger = async () => {
    if (!getAdminKey()) {
      setError("Въведете администраторски ключ в горната лента, за да стартирате scraping.");
      return;
    }
    if (!triggerSource) {
      setError("Изберете източник.");
      return;
    }
    setTriggering(true);
    setError(null);
    try {
      await api<ScrapeRun>("/scrape-runs", {
        method: "POST",
        body: JSON.stringify({
          source_id: triggerSource,
          max_pages: Number(maxPages) || 1,
          max_listings: Number(maxListings) || 5,
        }),
      });
      await load(1);
      setPage(1);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setTriggering(false);
    }
  };

  const openRun = async (run: ScrapeRun) => {
    setSelectedLoading(true);
    try {
      const detail = await api<ScrapeRun>(`/scrape-runs/${run.id}`);
      setSelected(detail);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSelectedLoading(false);
    }
  };

  const retry = async (run: ScrapeRun) => {
    if (!getAdminKey()) {
      setError("Въведете администраторски ключ.");
      return;
    }
    try {
      await api<ScrapeRun>(`/scrape-runs/${run.id}/retry`, { method: "POST" });
      await load(page);
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  if (loading && !data) return <Loading label="Зареждане на scraping задачите…" />;

  return (
    <div className="space-y-5">
      {error && <ErrorBox message={error} onRetry={() => void load(page)} />}

      <section className="card p-4">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <Play size={16} className="text-accent" /> Стартирай scraping
        </h2>
        <div className="grid gap-3 md:grid-cols-4">
          <div>
            <label className="label">Източник</label>
            <select className="input" value={triggerSource} onChange={(event) => setTriggerSource(event.target.value)}>
              <option value="">Изберете</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id} disabled={!source.enabled || source.status !== "verified"}>
                  {source.name} {source.status !== "verified" ? `(${statusLabel(source.status)})` : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Макс. страници</label>
            <input className="input" type="number" min={1} max={20} value={maxPages} onChange={(event) => setMaxPages(event.target.value)} />
          </div>
          <div>
            <label className="label">Макс. обяви</label>
            <input className="input" type="number" min={1} max={100} value={maxListings} onChange={(event) => setMaxListings(event.target.value)} />
          </div>
          <div className="flex items-end">
            <button className="btn-primary w-full" onClick={() => void trigger()} disabled={triggering}>
              {triggering ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
              {triggering ? "Стартиране…" : "Стартирай"}
            </button>
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Само проверени източници. Лимитите се прилагат и от конфигурацията на източника.
        </p>
      </section>

      {selected && (
        <section className="card p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-white">Детайли за задача</h2>
              <p className="text-xs text-slate-500">{selected.id}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={runStatusTone(selected.status)}>{statusLabel(selected.status)}</Badge>
              <button className="btn-ghost px-2.5 py-1.5 text-xs" onClick={() => setSelected(null)}>
                Затвори
              </button>
            </div>
          </div>
          {selectedLoading ? (
            <Loading label="Зареждане…" />
          ) : (
            <>
              <div className="grid gap-2 text-xs text-slate-400 sm:grid-cols-2 lg:grid-cols-4">
                <span>Страници: {selected.pages_fetched}</span>
                <span>Намерени: {selected.listings_found}</span>
                <span>Създадени: {selected.listings_created}</span>
                <span>Обновени: {selected.listings_updated}</span>
                <span>Без промяна: {selected.listings_unchanged}</span>
                <span>Грешки: {selected.errors_count}</span>
                <span>Старт: {formatDate(selected.started_at)}</span>
                <span>Край: {formatDate(selected.completed_at)}</span>
              </div>
              {selected.error_message && (
                <p className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
                  {selected.error_message}
                </p>
              )}
              {selected.errors && selected.errors.length > 0 && (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr>
                        <th className="table-head py-2">Време</th>
                        <th className="table-head py-2">Тип</th>
                        <th className="table-head py-2">Съобщение</th>
                        <th className="table-head py-2">URL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.errors.map((item) => (
                        <tr key={item.id} className="border-t border-edge/40">
                          <td className="py-2 text-slate-500">{formatDate(item.occurred_at)}</td>
                          <td className="py-2 text-rose-300">{item.error_type}</td>
                          <td className="max-w-[360px] py-2 text-slate-300">{item.message}</td>
                          <td className="max-w-[260px] truncate py-2 text-slate-500">
                            {item.url ? (
                              <a href={item.url} target="_blank" rel="noreferrer" className="hover:text-accent">
                                {item.url}
                              </a>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </section>
      )}

      <section className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-edge/60 px-4 py-3">
          <h2 className="text-sm font-semibold text-white">История</h2>
          <button className="btn-ghost px-2.5 py-1.5 text-xs" onClick={() => void load(page)}>
            <RefreshCw size={14} /> Обнови
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-edge/50 bg-ink/40">
              <tr>
                <th className="table-head px-4 py-3">Статус</th>
                <th className="table-head px-4 py-3">Източник</th>
                <th className="table-head px-4 py-3">Намерени</th>
                <th className="table-head px-4 py-3">Нови</th>
                <th className="table-head px-4 py-3">Обновени</th>
                <th className="table-head px-4 py-3">Грешки</th>
                <th className="table-head px-4 py-3">Времетраене</th>
                <th className="table-head px-4 py-3">Старт</th>
                <th className="table-head px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((run) => (
                <tr key={run.id} className="border-b border-edge/30 last:border-0">
                  <td className="px-4 py-2.5">
                    <Badge tone={runStatusTone(run.status)}>{statusLabel(run.status)}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-slate-300">{sourceName(run.source_id)}</td>
                  <td className="px-4 py-2.5 text-slate-400">{formatNumber(run.listings_found)}</td>
                  <td className="px-4 py-2.5 text-emerald-300">{formatNumber(run.listings_created)}</td>
                  <td className="px-4 py-2.5 text-sky-300">{formatNumber(run.listings_updated)}</td>
                  <td className="px-4 py-2.5 text-rose-300">{formatNumber(run.errors_count)}</td>
                  <td className="px-4 py-2.5 text-slate-400">{duration(run)}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{formatDate(run.created_at)}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center justify-end gap-1">
                      <button className="btn-ghost px-2 py-1 text-xs" onClick={() => void openRun(run)}>
                        Детайли
                      </button>
                      {run.status === "failed" && (
                        <button className="btn-ghost px-2 py-1 text-xs" onClick={() => void retry(run)}>
                          <RotateCcw size={13} /> Retry
                        </button>
                      )}
                      <Link to={`/errors?run=${run.id}`} className="btn-ghost px-2 py-1 text-xs">
                        Грешки
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
              {data && data.items.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-sm text-slate-500">
                    Няма scraping задачи.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
