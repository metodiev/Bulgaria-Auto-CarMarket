import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, RefreshCw } from "lucide-react";
import { api, formatApiError } from "../api/client";
import type { AIAnalysisRun, Page } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import { formatDate, formatNumber, runStatusTone, statusLabel, taskLabel } from "../lib/format";

export default function AIResults() {
  const [data, setData] = useState<Page<AIAnalysisRun> | null>(null);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({ page: String(page), page_size: "20" });
      if (status) query.set("status", status);
      setData(await api<Page<AIAnalysisRun>>(`/ai/results?${query.toString()}`));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [page, status]);

  const active = useMemo(
    () => data?.items.some((run) => run.status === "running" || run.status === "pending") ?? false,
    [data],
  );

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => void load(false), 4000);
    return () => window.clearInterval(timer);
  }, [active, page, status]);

  if (loading && !data) return <Loading label="Зареждане на AI анализите…" />;

  return (
    <div className="space-y-5">
      {error && <ErrorBox message={error} onRetry={() => void load()} />}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <label className="label">Статус</label>
          <select className="input w-48" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
            <option value="">Всички</option>
            <option value="pending">Чака</option>
            <option value="running">Изпълнява се</option>
            <option value="completed">Завършен</option>
            <option value="failed">Неуспешен</option>
            <option value="cancelled">Отказан</option>
          </select>
        </div>
        <button className="btn-ghost" onClick={() => void load()}>
          <RefreshCw size={16} /> Обнови
        </button>
      </div>

      <section className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-edge/50 bg-ink/40">
              <tr>
                <th className="table-head px-4 py-3">Статус</th>
                <th className="table-head px-4 py-3">Задача</th>
                <th className="table-head px-4 py-3">Модел</th>
                <th className="table-head px-4 py-3">Кандидати</th>
                <th className="table-head px-4 py-3">Прогрес</th>
                <th className="table-head px-4 py-3">Създаден</th>
                <th className="table-head px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((run) => (
                <tr key={run.id} className="border-b border-edge/30 last:border-0">
                  <td className="px-4 py-2.5">
                    <Badge tone={runStatusTone(run.status)}>{statusLabel(run.status)}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-slate-200">{taskLabel(run.task_type)}</td>
                  <td className="px-4 py-2.5 text-slate-400">{run.model_name}</td>
                  <td className="px-4 py-2.5 text-slate-400">{formatNumber(run.input_count)}</td>
                  <td className="px-4 py-2.5">
                    <div className="h-1.5 w-28 overflow-hidden rounded-full bg-ink">
                      <div className="h-full rounded-full bg-accent" style={{ width: `${run.progress}%` }} />
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-xs text-slate-500">{formatDate(run.created_at)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <Link to={`/ai/results/${run.id}`} className="btn-ghost px-2.5 py-1 text-xs">
                      <Bot size={13} /> Отвори
                    </Link>
                  </td>
                </tr>
              ))}
              {data && data.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-slate-500">
                    Няма AI анализи. Стартирайте ръчен анализ от AI настройките.
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
