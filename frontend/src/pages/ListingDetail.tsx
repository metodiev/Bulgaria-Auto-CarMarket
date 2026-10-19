import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, MapPin, Phone, User } from "lucide-react";
import { api, formatApiError } from "../api/client";
import type { Listing, PricePoint } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import PriceChart from "../components/PriceChart";
import {
  bodyLabel,
  driveLabel,
  formatDate,
  formatKm,
  formatNumber,
  formatPrice,
  fuelLabel,
  statusLabel,
  transmissionLabel,
} from "../lib/format";

function Spec({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-xl border border-edge/50 bg-ink/30 px-3 py-2">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-200">{value ?? "—"}</dd>
    </div>
  );
}

export default function ListingDetail() {
  const { id } = useParams<{ id: string }>();
  const [listing, setListing] = useState<Listing | null>(null);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [selectedImage, setSelectedImage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api<Listing>(`/listings/${id}`),
      api<PricePoint[]>(`/listings/${id}/price-history`).catch(() => []),
    ])
      .then(([item, points]) => {
        setListing(item);
        setHistory(points);
        setSelectedImage(0);
      })
      .catch((err) => setError(formatApiError(err)))
      .finally(() => setLoading(false));
  }, [id, reloadKey]);

  if (loading) return <Loading label="Зареждане на обявата…" />;
  if (error)
    return (
      <ErrorBox message={error} onRetry={() => setReloadKey((value) => value + 1)} />
    );
  if (!listing) return null;

  const images = listing.images?.map((image) => image.original_url) ?? [];
  const mainImage = images[selectedImage] ?? listing.primary_image_url;
  const sourceUrl = listing.canonical_url;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/listings" className="btn-ghost">
          <ArrowLeft size={16} /> Назад към обявите
        </Link>
        <a href={sourceUrl} target="_blank" rel="noreferrer" className="btn-primary">
          <ExternalLink size={16} /> Оригинална обява
        </a>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
        <section className="space-y-5">
          <div className="card overflow-hidden">
            <div className="aspect-[16/10] bg-ink">
              {mainImage ? (
                <img src={mainImage} alt={listing.title} className="h-full w-full object-cover" />
              ) : (
                <div className="grid h-full place-items-center text-sm text-slate-600">Няма снимка</div>
              )}
            </div>
            {images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto p-3">
                {images.map((url, index) => (
                  <button
                    key={url}
                    onClick={() => setSelectedImage(index)}
                    className={`h-16 w-24 shrink-0 overflow-hidden rounded-lg border transition ${
                      index === selectedImage ? "border-accent" : "border-edge/60 opacity-70 hover:opacity-100"
                    }`}
                  >
                    <img src={url} alt="" loading="lazy" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="card p-4">
            <h2 className="mb-3 text-sm font-semibold text-white">Описание</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">
              {listing.description || "Няма описание."}
            </p>
          </div>

          <div className="card p-4">
            <h2 className="mb-3 text-sm font-semibold text-white">История на цената</h2>
            <PriceChart points={history} currency={listing.currency} />
          </div>
        </section>

        <aside className="space-y-5">
          <div className="card p-5">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge tone="neutral">{listing.source.name}</Badge>
              <Badge tone={listing.status === "active" ? "success" : "warning"}>{statusLabel(listing.status)}</Badge>
            </div>
            <h1 className="text-xl font-bold leading-snug text-white">{listing.title}</h1>
            <p className="mt-3 text-3xl font-extrabold text-accent">
              {formatPrice(listing.price, listing.currency)}
            </p>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
              <span className="inline-flex items-center gap-1">
                <MapPin size={13} /> {listing.city ?? listing.region ?? "—"}
              </span>
              <span className="inline-flex items-center gap-1">
                <User size={13} /> {listing.seller_type === "private" ? "частно лице" : "търговец"}
              </span>
              {listing.source.slug === "cars-bg" && (
                <span className="inline-flex items-center gap-1">
                  <Phone size={13} /> виж телефона в оригинала
                </span>
              )}
            </div>
          </div>

          <div className="card p-4">
            <h2 className="mb-3 text-sm font-semibold text-white">Характеристики</h2>
            <dl className="grid grid-cols-2 gap-2">
              <Spec label="Марка" value={listing.make} />
              <Spec label="Модел" value={listing.model} />
              <Spec label="Година" value={listing.year} />
              <Spec label="Пробег" value={formatKm(listing.mileage_km)} />
              <Spec label="Гориво" value={fuelLabel(listing.fuel_type)} />
              <Spec label="Кутия" value={transmissionLabel(listing.transmission)} />
              <Spec label="Мощност" value={listing.power_hp ? `${formatNumber(listing.power_hp)} к.с.` : null} />
              <Spec label="Двигател" value={listing.engine_volume ? `${listing.engine_volume} л` : null} />
              <Spec label="Купе" value={bodyLabel(listing.body_type)} />
              <Spec label="Задвижване" value={driveLabel(listing.drivetrain)} />
              <Spec label="Състояние" value={listing.condition} />
              <Spec label="Цвят" value={listing.color} />
              <Spec label="Регион" value={listing.region} />
              <Spec label="Град" value={listing.city} />
              <Spec label="Първо видяна" value={formatDate(listing.first_seen_at)} />
              <Spec label="Последно видяна" value={formatDate(listing.last_seen_at)} />
            </dl>
          </div>

          <div className="card p-4 text-xs leading-relaxed text-slate-500">
            <p>
              ID: <span className="text-slate-400">{listing.source_listing_id}</span>
            </p>
            <p className="mt-1 break-all">
              URL:{" "}
              <a href={sourceUrl} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                {sourceUrl}
              </a>
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
