import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Ban, ExternalLink, RefreshCw, RotateCcw, Sparkles } from "lucide-react";
import { api, formatApiError, getAdminKey } from "../api/client";
import type { AIAnalysisResult } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import {
  formatDate,
  formatKm,
  formatNumber,
  formatPrice,
  runStatusTone,
  statusLabel,
  taskLabel,
} from "../lib/format";

export default function AIResultDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<AIAnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  const load = async (showSpinner = true) => {
    if (!id) return;
    if (showSpinner) setLoading(true);
    setError(null);
    try {
      setResult(await api<AIAnalysisResult>(`/ai/results/${id}`));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [id]);

  useEffect(() => {
    if (!result || (result.status !== "pending" && result.status !== "running")) return;
    const timer = window.setInterval(() => void load(false), 3000);
    return () => window.clearInterval(timer);
  }, [result?.status, id]);

  const retry = async () => {
    if (!id || !getAdminKey()) {
      setError("Въведете администраторски ключ, за да повторите анализа.");
      return;
    }
    setRetrying(true);
    try {
      const run = await api<{ id: string }>(`/ai/jobs/${id}/retry`, { method: "POST" });
      navigate(`/ai/results/${run.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setRetrying(false);
    }
  };

  const cancel = async () => {
    if (!id || !getAdminKey()) {
      setError("Въведете администраторски ключ, за да откажете анализа.");
      return;
    }
    try {
      await api(`/ai/jobs/${id}/cancel`, { method: "POST" });
      await load(false);
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  if (loading) return <Loading label="Зареждане на AI резултата…" />;
  if (error && !result) return <ErrorBox message={error} onRetry={() => void load()} />;
  if (!result) return null;

  const output = result.output;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/ai/results" className="btn-ghost">
          <ArrowLeft size={16} /> Назад към анализите
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={runStatusTone(result.status)}>{statusLabel(result.status)}</Badge>
          {(result.status === "pending" || result.status === "running") && (
            <button className="btn-ghost" onClick={() => void cancel()}>
              <Ban size={15} /> Откажи
            </button>
          )}
          {(result.status === "failed" || result.status === "cancelled") && (
            <button className="btn-primary" onClick={() => void retry()} disabled={retrying}>
              {retrying ? <RefreshCw className="animate-spin" size={15} /> : <RotateCcw size={15} />}
              Повтори
            </button>
          )}
        </div>
      </div>

      {error && <ErrorBox message={error} onRetry={() => void load()} />}

      <section className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-bold text-white">
              <Sparkles size={19} className="text-accent" /> {taskLabel(result.task_type)}
            </h1>
            <p className="mt-1 text-xs text-slate-500">
              {result.model_name} · prompt {result.prompt_version} · {formatDate(result.created_at)}
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="rounded-xl bg-ink/50 px-3 py-2">
              <p className="text-slate-500">Кандидати</p>
              <p className="mt-0.5 text-base font-bold text-white">{formatNumber(result.input_count)}</p>
            </div>
            <div className="rounded-xl bg-ink/50 px-3 py-2">
              <p className="text-slate-500">Опит</p>
              <p className="mt-0.5 text-base font-bold text-white">{result.attempt || "—"}</p>
            </div>
            <div className="rounded-xl bg-ink/50 px-3 py-2">
              <p className="text-slate-500">Времетраене</p>
              <p className="mt-0.5 text-base font-bold text-white">
                {result.duration_ms ? `${Math.round(result.duration_ms / 1000)}s` : "—"}
              </p>
            </div>
          </div>
        </div>
        {(result.status === "running" || result.status === "pending") && (
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-slate-500">
              <span>Прогрес</span>
              <span>{result.progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ink">
              <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${result.progress}%` }} />
            </div>
          </div>
        )}
        {result.error_message && (
          <p className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
            {result.error_message}
          </p>
        )}
      </section>

      {output ? (
        <>
          <section className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
            <div className="card p-5">
              <h2 className="mb-2 text-sm font-semibold text-white">Резюме</h2>
              <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">{output.summary}</p>
              <h3 className="mt-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Методология</h3>
              <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-slate-400">{output.methodology}</p>
            </div>
            <div className="card p-5">
              <h2 className="mb-3 text-sm font-semibold text-white">Оценка</h2>
              <p className="text-3xl font-extrabold text-accent">{output.confidence}/10</p>
              <p className="mt-1 text-xs text-slate-500">увереност на модела</p>
              {output.price_comparison && (
                <p className="mt-4 text-sm leading-relaxed text-slate-300">{output.price_comparison}</p>
              )}
              {(output._validation ?? output.validation)?.warnings?.length ? (
                <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                  <p className="mb-1 font-semibold">Валидация</p>
                  {(output._validation ?? output.validation)?.warnings.map((warning) => (
                    <p key={warning}>{warning}</p>
                  ))}
                </div>
              ) : null}
            </div>
          </section>

          {output.ranking.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-white">Класация</h2>
              {output.ranking.map((item) => {
                const details = output.candidate_details?.[item.listing_id];
                return (
                  <article key={`${item.rank}-${item.listing_id}`} className="card p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="grid h-7 w-7 place-items-center rounded-full bg-accent/15 text-xs font-bold text-accent">
                            {item.rank}
                          </span>
                          <Link
                            to={`/listings/${item.listing_id}`}
                            className="max-w-[640px] truncate text-sm font-semibold text-slate-100 hover:text-accent"
                          >
                            {details?.title ?? item.listing_id}
                          </Link>
                        </div>
                        {details && (
                          <p className="mt-1 text-xs text-slate-500">
                            {details.year ?? "—"} · {formatKm(details.mileage_km)} ·{" "}
                            <span className="font-semibold text-accent">{formatPrice(details.price, details.currency)}</span>
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {item.score !== null && (
                          <Badge tone="info">score {item.score.toFixed(1)}</Badge>
                        )}
                        <Badge tone={item.confidence >= 7 ? "success" : item.confidence >= 4 ? "warning" : "danger"}>
                          confidence {item.confidence}/10
                        </Badge>
                      </div>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-slate-300">{item.reasoning}</p>
                    {item.price_comparison && (
                      <p className="mt-2 text-sm text-slate-400">{item.price_comparison}</p>
                    )}
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">Плюсове</p>
                        <ul className="mt-1 space-y-1 text-xs text-slate-400">
                          {item.pros.length > 0 ? item.pros.map((pro) => <li key={pro}>+ {pro}</li>) : <li>—</li>}
                        </ul>
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-rose-400">Минуси</p>
                        <ul className="mt-1 space-y-1 text-xs text-slate-400">
                          {item.cons.length > 0 ? item.cons.map((con) => <li key={con}>− {con}</li>) : <li>—</li>}
                        </ul>
                      </div>
                    </div>
                    {details && (
                      <a
                        href={details.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline"
                      >
                        Оригинална обява <ExternalLink size={12} />
                      </a>
                    )}
                  </article>
                );
              })}
            </section>
          )}

          <section className="grid gap-4 md:grid-cols-2">
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-semibold text-white">Общи плюсове</h2>
              <ul className="space-y-1 text-sm text-slate-400">
                {output.pros.length > 0 ? output.pros.map((item) => <li key={item}>+ {item}</li>) : <li>—</li>}
              </ul>
            </div>
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-semibold text-white">Общи минуси</h2>
              <ul className="space-y-1 text-sm text-slate-400">
                {output.cons.length > 0 ? output.cons.map((item) => <li key={item}>− {item}</li>) : <li>—</li>}
              </ul>
            </div>
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-semibold text-white">Ограничения</h2>
              <ul className="space-y-1 text-sm text-slate-400">
                {output.limitations.length > 0 ? output.limitations.map((item) => <li key={item}>{item}</li>) : <li>—</li>}
              </ul>
            </div>
            <div className="card p-4">
              <h2 className="mb-2 text-sm font-semibold text-white">Оригинални URL адреси</h2>
              <ul className="space-y-1 text-sm">
                {output.original_urls.length > 0 ? (
                  output.original_urls.map((url) => (
                    <li key={url} className="truncate">
                      <a href={url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                        {url}
                      </a>
                    </li>
                  ))
                ) : (
                  <li className="text-slate-400">—</li>
                )}
              </ul>
            </div>
          </section>
        </>
      ) : (
        <section className="card grid place-items-center px-4 py-14 text-center">
          <p className="text-sm text-slate-400">
            {result.status === "completed"
              ? "Анализът е завършен, но няма структуриран резултат."
              : "Резултатът ще се появи след завършване на задачата."}
          </p>
          <button className="btn-ghost mt-3" onClick={() => void load()}>
            <RefreshCw size={15} /> Обнови
          </button>
        </section>
      )}
    </div>
  );
}
