import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Filter, LayoutGrid, List, RotateCcw, Search } from "lucide-react";
import { api, buildQuery, formatApiError } from "../api/client";
import type { Listing, ListingFilterOptions, Page } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import {
  formatDateShort,
  formatKm,
  formatPrice,
  fuelLabel,
  transmissionLabel,
} from "../lib/format";

interface FilterState {
  q: string;
  make: string;
  model: string;
  year_from: string;
  year_to: string;
  price_from: string;
  price_to: string;
  mileage_from: string;
  mileage_to: string;
  region: string;
  fuel_type: string;
  transmission: string;
  source: string;
  sort_by: string;
  sort_order: string;
}

const EMPTY_FILTERS: FilterState = {
  q: "",
  make: "",
  model: "",
  year_from: "",
  year_to: "",
  price_from: "",
  price_to: "",
  mileage_from: "",
  mileage_to: "",
  region: "",
  fuel_type: "",
  transmission: "",
  source: "",
  sort_by: "last_seen_at",
  sort_order: "desc",
};

export default function Listings() {
  const [options, setOptions] = useState<ListingFilterOptions | null>(null);
  const [draft, setDraft] = useState<FilterState>(EMPTY_FILTERS);
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(24);
  const [data, setData] = useState<Page<Listing> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"table" | "gallery">("table");

  useEffect(() => {
    api<ListingFilterOptions>("/listings/filters")
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const query = buildQuery({ ...filters, page, page_size: pageSize });
    api<Page<Listing>>(`/listings${query}`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(formatApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters, page, pageSize]);

  const update = (field: keyof FilterState, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }));
  };

  const applyFilters = () => {
    setFilters({ ...draft });
    setPage(1);
  };

  const resetFilters = () => {
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setPage(1);
  };

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <Filter size={16} className="text-accent" /> Филтри
        </div>
        <form
          className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault();
            applyFilters();
          }}
        >
          <div className="xl:col-span-2">
            <label className="label">Търсене</label>
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-2.5 text-slate-500" />
              <input
                className="input pl-9"
                placeholder="Марка, модел, текст…"
                value={draft.q}
                onChange={(event) => update("q", event.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="label">Марка</label>
            <select className="input" value={draft.make} onChange={(event) => update("make", event.target.value)}>
              <option value="">Всички</option>
              {options?.makes.map((make) => (
                <option key={make} value={make}>
                  {make}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Модел</label>
            <input
              className="input"
              placeholder="напр. A4"
              value={draft.model}
              onChange={(event) => update("model", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Година от</label>
            <input
              className="input"
              type="number"
              placeholder="2010"
              value={draft.year_from}
              onChange={(event) => update("year_from", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Година до</label>
            <input
              className="input"
              type="number"
              placeholder="2024"
              value={draft.year_to}
              onChange={(event) => update("year_to", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Цена от (EUR)</label>
            <input
              className="input"
              type="number"
              placeholder="5000"
              value={draft.price_from}
              onChange={(event) => update("price_from", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Цена до (EUR)</label>
            <input
              className="input"
              type="number"
              placeholder="30000"
              value={draft.price_to}
              onChange={(event) => update("price_to", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Км от</label>
            <input
              className="input"
              type="number"
              placeholder="0"
              value={draft.mileage_from}
              onChange={(event) => update("mileage_from", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Км до</label>
            <input
              className="input"
              type="number"
              placeholder="300000"
              value={draft.mileage_to}
              onChange={(event) => update("mileage_to", event.target.value)}
            />
          </div>
          <div>
            <label className="label">Регион</label>
            <select className="input" value={draft.region} onChange={(event) => update("region", event.target.value)}>
              <option value="">Всички</option>
              {options?.regions.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Гориво</label>
            <select
              className="input"
              value={draft.fuel_type}
              onChange={(event) => update("fuel_type", event.target.value)}
            >
              <option value="">Всички</option>
              {options?.fuel_types.map((fuel) => (
                <option key={fuel} value={fuel}>
                  {fuelLabel(fuel)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Скоростна кутия</label>
            <select
              className="input"
              value={draft.transmission}
              onChange={(event) => update("transmission", event.target.value)}
            >
              <option value="">Всички</option>
              {options?.transmissions.map((transmission) => (
                <option key={transmission} value={transmission}>
                  {transmissionLabel(transmission)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Източник</label>
            <select className="input" value={draft.source} onChange={(event) => update("source", event.target.value)}>
              <option value="">Всички</option>
              {options?.sources.map((source) => (
                <option key={source.slug} value={source.slug}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Сортиране</label>
            <select className="input" value={draft.sort_by} onChange={(event) => update("sort_by", event.target.value)}>
              <option value="last_seen_at">Последно видяна</option>
              <option value="price">Цена</option>
              <option value="mileage_km">Пробег</option>
              <option value="year">Година</option>
              <option value="first_seen_at">Първо видяна</option>
              <option value="title">Заглавие</option>
            </select>
          </div>
          <div>
            <label className="label">Посока</label>
            <select
              className="input"
              value={draft.sort_order}
              onChange={(event) => update("sort_order", event.target.value)}
            >
              <option value="desc">Низходящо</option>
              <option value="asc">Възходящо</option>
            </select>
          </div>
          <div className="flex items-end gap-2 xl:col-span-2">
            <button type="submit" className="btn-primary flex-1">
              <Search size={16} /> Покажи
            </button>
            <button type="button" className="btn-ghost" onClick={resetFilters}>
              <RotateCcw size={16} /> Изчисти
            </button>
          </div>
        </form>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          {data ? `${data.total} обяви` : "Зареждане…"}
        </p>
        <div className="flex items-center gap-1 rounded-xl border border-edge p-1">
          <button
            className={`rounded-lg px-2.5 py-1.5 ${view === "table" ? "bg-accent/15 text-accent" : "text-slate-400"}`}
            onClick={() => setView("table")}
            aria-label="Таблица"
          >
            <List size={16} />
          </button>
          <button
            className={`rounded-lg px-2.5 py-1.5 ${view === "gallery" ? "bg-accent/15 text-accent" : "text-slate-400"}`}
            onClick={() => setView("gallery")}
            aria-label="Галерия"
          >
            <LayoutGrid size={16} />
          </button>
        </div>
      </div>

      {error && <ErrorBox message={error} onRetry={() => setFilters({ ...filters })} />}

      {loading ? (
        <Loading label="Зареждане на обяви…" />
      ) : !data || data.items.length === 0 ? (
        <div className="card grid place-items-center px-4 py-16 text-center">
          <p className="text-sm text-slate-400">Няма обяви по тези филтри.</p>
          <button className="btn-ghost mt-3" onClick={resetFilters}>
            Изчисти филтрите
          </button>
        </div>
      ) : view === "table" ? (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-edge/60 bg-ink/40">
                <tr>
                  <th className="table-head px-4 py-3">Автомобил</th>
                  <th className="table-head px-4 py-3">Година</th>
                  <th className="table-head px-4 py-3">Цена</th>
                  <th className="table-head px-4 py-3">Пробег</th>
                  <th className="table-head px-4 py-3">Гориво</th>
                  <th className="table-head px-4 py-3">Регион</th>
                  <th className="table-head px-4 py-3">Източник</th>
                  <th className="table-head px-4 py-3">Видяна</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((listing) => (
                  <tr key={listing.id} className="border-b border-edge/30 transition hover:bg-white/[0.025] last:border-0">
                    <td className="px-4 py-2.5">
                      <Link to={`/listings/${listing.id}`} className="flex items-center gap-3">
                        <span className="h-11 w-16 shrink-0 overflow-hidden rounded-lg bg-ink">
                          {listing.primary_image_url ? (
                            <img
                              src={listing.primary_image_url}
                              alt=""
                              loading="lazy"
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <span className="grid h-full w-full place-items-center text-[10px] text-slate-600">N/A</span>
                          )}
                        </span>
                        <span className="min-w-0">
                          <span className="block max-w-[320px] truncate font-medium text-slate-200">
                            {listing.title}
                          </span>
                          <span className="block text-xs text-slate-500">
                            {[listing.make, listing.model].filter(Boolean).join(" · ") || "—"}
                          </span>
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-slate-300">{listing.year ?? "—"}</td>
                    <td className="px-4 py-2.5 font-semibold text-white">
                      {formatPrice(listing.price, listing.currency)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-300">{formatKm(listing.mileage_km)}</td>
                    <td className="px-4 py-2.5 text-slate-400">{fuelLabel(listing.fuel_type)}</td>
                    <td className="px-4 py-2.5 text-slate-400">{listing.city ?? listing.region ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      <Badge tone="neutral">{listing.source.name}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">{formatDateShort(listing.last_seen_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.items.map((listing) => (
            <Link
              key={listing.id}
              to={`/listings/${listing.id}`}
              className="card group overflow-hidden transition hover:-translate-y-0.5 hover:border-accent/40"
            >
              <div className="aspect-[16/10] overflow-hidden bg-ink">
                {listing.primary_image_url ? (
                  <img
                    src={listing.primary_image_url}
                    alt={listing.title}
                    loading="lazy"
                    className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
                  />
                ) : (
                  <div className="grid h-full place-items-center text-xs text-slate-600">Няма снимка</div>
                )}
              </div>
              <div className="space-y-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="line-clamp-2 text-sm font-semibold text-slate-100">{listing.title}</h2>
                  <Badge tone="neutral">{listing.source.name}</Badge>
                </div>
                <p className="text-lg font-bold text-accent">{formatPrice(listing.price, listing.currency)}</p>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-400">
                  <span>{listing.year ?? "—"}</span>
                  <span>{formatKm(listing.mileage_km)}</span>
                  <span>{fuelLabel(listing.fuel_type)}</span>
                  <span>{transmissionLabel(listing.transmission)}</span>
                </div>
                <p className="text-xs text-slate-500">{listing.city ?? listing.region ?? "—"}</p>
              </div>
            </Link>
          ))}
        </div>
      )}

      {data && (
        <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
      )}
    </div>
  );
}
