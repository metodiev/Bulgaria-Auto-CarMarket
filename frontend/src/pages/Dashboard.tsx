import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Car, Euro, TrendingDown } from "lucide-react";
import { api, formatApiError } from "../api/client";
import type { MarketStats, Page, ScrapeRun, Source } from "../api/types";
import BarList from "../components/BarList";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import StatCard from "../components/StatCard";
import {
  formatDate,
  formatNumber,
  formatPrice,
  runStatusTone,
  sourceStatusTone,
  statusLabel,
} from "../lib/format";

export default function Dashboard() {
  const [stats, setStats] = useState<MarketStats | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [market, sourceList, runPage] = await Promise.all([
        api<MarketStats>("/statistics/market"),
        api<Source[]>("/sources"),
        api<Page<ScrapeRun>>("/scrape-runs?page=1&page_size=6"),
      ]);
      setStats(market);
      setSources(sourceList);
      setRuns(runPage.items);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <Loading label="Зареждане на пазарните данни…" />;
  if (error) return <ErrorBox message={error} onRetry={() => void load()} />;
  if (!stats) return null;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Активни обяви"
          value={formatNumber(stats.total_active)}
          hint={`${formatNumber(stats.new_last_7_days)} нови през последните 7 дни`}
          icon={Car}
        />
        <StatCard
          label="Средна цена"
          value={formatPrice(stats.avg_price)}
          hint={`Медиана: ${formatPrice(stats.median_price)}`}
          icon={Euro}
        />
        <StatCard
          label="Ценови промени"
          value={formatNumber(stats.price_changes_30d)}
          hint="Наблюдавани през последните 30 дни"
          icon={TrendingDown}
        />
        <StatCard
          label="Източници"
          value={`${sources.filter((source) => source.enabled).length}/${sources.length}`}
          hint="Активни спрямо всички регистрирани"
          icon={Activity}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <BarList title="По марка" buckets={stats.by_make} />
        <BarList title="По модел" buckets={stats.by_model} />
        <BarList title="По регион" buckets={stats.by_region} />
        <BarList title="По източник" buckets={stats.by_source} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-edge/60 px-4 py-3">
            <h2 className="text-sm font-semibold text-white">Последни scraping задачи</h2>
            <Link to="/scrape-runs" className="text-xs font-semibold text-accent hover:underline">
              Всички задачи
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/50 bg-ink/40">
                <tr>
                  <th className="table-head px-4 py-2.5">Статус</th>
                  <th className="table-head px-4 py-2.5">Обяви</th>
                  <th className="table-head px-4 py-2.5">Грешки</th>
                  <th className="table-head px-4 py-2.5">Създадена</th>
                </tr>
              </thead>
              <tbody>
                {runs.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-xs text-slate-500">
                      Все още няма scraping задачи. Стартирайте първата от страница Scraping.
                    </td>
                  </tr>
                )}
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-edge/30 last:border-0">
                    <td className="px-4 py-2.5">
                      <Badge tone={runStatusTone(run.status)}>{statusLabel(run.status)}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-slate-300">
                      {formatNumber(run.listings_created + run.listings_updated)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-400">{formatNumber(run.errors_count)}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">{formatDate(run.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Източници</h2>
            <Link to="/sources" className="text-xs font-semibold text-accent hover:underline">
              Управление
            </Link>
          </div>
          <div className="space-y-2">
            {sources.map((source) => (
              <div
                key={source.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-edge/50 bg-ink/30 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">{source.name}</p>
                  <p className="text-[11px] text-slate-500">{formatNumber(source.listing_count)} обяви</p>
                </div>
                <Badge tone={sourceStatusTone(source.status)}>{statusLabel(source.status)}</Badge>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <BarList title="По гориво" buckets={stats.by_fuel} />
        <BarList title="По година" buckets={stats.by_year} />
      </section>
    </div>
  );
}
