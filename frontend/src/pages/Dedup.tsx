import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Copy, XCircle } from "lucide-react";
import { api, formatApiError, getAdminKey } from "../api/client";
import type { DedupCandidate } from "../api/types";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import { formatKm, formatPrice } from "../lib/format";

function ListingBrief({
  listing,
  label,
}: {
  listing: DedupCandidate["listing_a"];
  label: string;
}) {
  return (
    <div className="rounded-xl border border-edge/60 bg-ink/30 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <Link to={`/listings/${listing.id}`} className="mt-1 block text-sm font-semibold text-slate-100 hover:text-accent">
        {listing.title}
      </Link>
      <p className="mt-1 text-sm font-bold text-accent">{formatPrice(listing.price, listing.currency)}</p>
      <p className="mt-1 text-xs text-slate-400">
        {listing.year ?? "—"} · {formatKm(listing.mileage_km)} · {listing.source.name}
      </p>
      <a href={listing.canonical_url} target="_blank" rel="noreferrer" className="mt-2 block truncate text-[11px] text-slate-500 hover:text-accent">
        {listing.canonical_url}
      </a>
    </div>
  );
}

export default function Dedup() {
  const [candidates, setCandidates] = useState<DedupCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setCandidates(await api<DedupCandidate[]>("/dedup/candidates?status=pending"));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const resolve = async (candidate: DedupCandidate, action: "duplicate" | "ignore") => {
    if (!getAdminKey()) {
      setError("Въведете администраторски ключ, за да решавате кандидати за дубликати.");
      return;
    }
    try {
      await api<DedupCandidate>(`/dedup/candidates/${candidate.id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      setCandidates((current) => current.filter((item) => item.id !== candidate.id));
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  if (loading) return <Loading label="Търсене на дубликати…" />;

  return (
    <div className="space-y-5">
      {error && <ErrorBox message={error} onRetry={() => void load()} />}

      <section className="card p-4 text-sm text-slate-400">
        <div className="flex items-start gap-3">
          <Copy className="mt-0.5 shrink-0 text-accent" size={18} />
          <p>
            Кандидатите се създават автоматично при сходни марка, модел, година, цена, пробег и
            локация. Само проверен източник може да бъде избран за канонична обява. Решението не
            изтрива историята на обявите.
          </p>
        </div>
      </section>

      {candidates.length === 0 ? (
        <div className="card grid place-items-center px-4 py-16 text-center">
          <CheckCircle2 size={34} className="text-emerald-400" />
          <p className="mt-3 text-sm text-slate-400">Няма чакащи кандидати за дубликати.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {candidates.map((candidate) => (
            <section key={candidate.id} className="card p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber-300 ring-1 ring-inset ring-amber-400/30">
                    score {(candidate.score * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs text-slate-500">
                    {Object.entries(candidate.reasons)
                      .map(([key, value]) => `${key}=${value}`)
                      .join(" · ")}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button className="btn-primary px-3 py-1.5 text-xs" onClick={() => void resolve(candidate, "duplicate")}>
                    <Copy size={14} /> Маркирай като дубликат
                  </button>
                  <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => void resolve(candidate, "ignore")}>
                    <XCircle size={14} /> Игнорирай
                  </button>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <ListingBrief listing={candidate.listing_a} label="Обява A" />
                <ListingBrief listing={candidate.listing_b} label="Обява B" />
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
