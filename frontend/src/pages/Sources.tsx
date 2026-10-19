import { useEffect, useState } from "react";
import { Activity, Clock, ChevronDown, ChevronUp, ExternalLink, ShieldAlert, Settings2 } from "lucide-react";
import { api, formatApiError, getAdminKey } from "../api/client";
import type { SearchJob, Source } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import { formatDate, formatNumber, sourceStatusTone, statusLabel } from "../lib/format";

interface ConfigDraft {
  max_pages_per_run: string;
  max_listings_per_run: string;
  requests_per_second: string;
  max_concurrency: string;
  download_images: boolean;
  archive_html: boolean;
}

function toConfigDraft(source: Source): ConfigDraft {
  return {
    max_pages_per_run: String(source.config.max_pages_per_run ?? 2),
    max_listings_per_run: String(source.config.max_listings_per_run ?? 20),
    requests_per_second: String(source.config.requests_per_second ?? 0.5),
    max_concurrency: String(source.config.max_concurrency ?? 1),
    download_images: Boolean(source.config.download_images ?? false),
    archive_html: Boolean(source.config.archive_html ?? false),
  };
}

export default function Sources() {
  const [sources, setSources] = useState<Source[]>([]);
  const [jobs, setJobs] = useState<SearchJob[]>([]);
  const [jobDrafts, setJobDrafts] = useState<Record<string, { enabled: boolean; interval: string }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<ConfigDraft | null>(null);
  const [saving, setSaving] = useState(false);
  const [savingJob, setSavingJob] = useState<string | null>(null);
  const [healthChecking, setHealthChecking] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sourceList, jobList] = await Promise.all([
        api<Source[]>("/sources"),
        api<SearchJob[]>("/search-jobs"),
      ]);
      setSources(sourceList);
      setJobs(jobList);
      setJobDrafts(
        Object.fromEntries(
          jobList.map((job) => [
            job.id,
            { enabled: job.enabled, interval: String(job.interval_minutes) },
          ]),
        ),
      );
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const requireKey = (): boolean => {
    if (getAdminKey()) return true;
    setError("Въведете администраторски ключ в горната лента, за да променяте източници.");
    return false;
  };

  const toggle = async (source: Source) => {
    if (!requireKey()) return;
    if (source.status !== "verified") {
      setError(
        `Източникът е със статус „${statusLabel(source.status)}“. Включването е блокирано от съображения за достъп.`,
      );
      return;
    }
    try {
      const updated = await api<Source>(`/sources/${source.id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !source.enabled }),
      });
      setSources((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  const checkHealth = async (source: Source) => {
    if (!requireKey()) return;
    setHealthChecking(source.id);
    try {
      const result = await api<{ ok: boolean; status?: string; message?: string }>(
        `/sources/${source.id}/health`,
        { method: "POST" },
      );
      setSources((current) =>
        current.map((item) =>
          item.id === source.id
            ? {
                ...item,
                last_health_status: result.ok ? "ok" : result.status ?? "error",
                last_health_checked_at: new Date().toISOString(),
              }
            : item,
        ),
      );
      if (!result.ok) {
        setError(result.message ?? `Статус: ${result.status ?? "error"}`);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setHealthChecking(null);
    }
  };

  const startEdit = (source: Source) => {
    setEditing(source.id);
    setDraft(toConfigDraft(source));
  };

  const saveConfig = async (source: Source) => {
    if (!requireKey() || !draft) return;
    setSaving(true);
    try {
      const updated = await api<Source>(`/sources/${source.id}`, {
        method: "PUT",
        body: JSON.stringify({
          config: {
            max_pages_per_run: Number(draft.max_pages_per_run) || 1,
            max_listings_per_run: Number(draft.max_listings_per_run) || 1,
            requests_per_second: Number(draft.requests_per_second) || 0.5,
            max_concurrency: Number(draft.max_concurrency) || 1,
            download_images: draft.download_images,
            archive_html: draft.archive_html,
          },
        }),
      });
      setSources((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setEditing(null);
      setDraft(null);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const saveJob = async (job: SearchJob) => {
    if (!requireKey()) return;
    const jobDraft = jobDrafts[job.id];
    if (!jobDraft) return;
    setSavingJob(job.id);
    try {
      const updated = await api<SearchJob>(`/search-jobs/${job.id}`, {
        method: "PUT",
        body: JSON.stringify({
          enabled: jobDraft.enabled,
          interval_minutes: Number(jobDraft.interval) || job.interval_minutes,
        }),
      });
      setJobs((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setJobDrafts((current) => ({
        ...current,
        [updated.id]: {
          enabled: updated.enabled,
          interval: String(updated.interval_minutes),
        },
      }));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSavingJob(null);
    }
  };

  if (loading) return <Loading label="Зареждане на източниците…" />;

  return (
    <div className="space-y-5">
      {error && <ErrorBox message={error} onRetry={() => void load()} />}

      <div className="card border-amber-500/20 bg-amber-500/[0.04] p-4 text-sm text-amber-100/90">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 shrink-0 text-amber-300" size={18} />
          <p>
            Само източници със статус <strong>Проверен</strong> могат да бъдат включвани.
            За останалите са документирани robots.txt и/или условия за ползване, които изискват
            изрично разрешение. Платформата не заобикаля CAPTCHA, анти-бот защити или ограничения.
          </p>
        </div>
      </div>

      {jobs.length > 0 && (
        <section className="card p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <Clock size={16} className="text-accent" /> Периодични scraping задачи
          </h2>
          <p className="mb-3 text-xs text-slate-500">
            По подразбиране са изключени. При включване scheduler-ът стартира задача на
            зададения интервал, с лимитите на източника.
          </p>
          <div className="space-y-2">
            {jobs.map((job) => {
              const jobDraft = jobDrafts[job.id] ?? {
                enabled: job.enabled,
                interval: String(job.interval_minutes),
              };
              return (
                <div
                  key={job.id}
                  className="flex flex-wrap items-center gap-3 rounded-xl border border-edge/60 bg-ink/30 px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-200">{job.name}</p>
                    <p className="text-[11px] text-slate-500">
                      {job.source.name} · последно: {formatDate(job.last_run_at)} · следващо:{" "}
                      {formatDate(job.next_run_at)}
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={jobDraft.enabled}
                      onChange={(event) =>
                        setJobDrafts((current) => ({
                          ...current,
                          [job.id]: { ...jobDraft, enabled: event.target.checked },
                        }))
                      }
                    />
                    активна
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-400">
                    интервал
                    <input
                      className="input w-24 py-1 text-xs"
                      type="number"
                      min={5}
                      max={10080}
                      value={jobDraft.interval}
                      onChange={(event) =>
                        setJobDrafts((current) => ({
                          ...current,
                          [job.id]: { ...jobDraft, interval: event.target.value },
                        }))
                      }
                    />
                    мин
                  </label>
                  <button
                    className="btn-primary px-3 py-1.5 text-xs"
                    onClick={() => void saveJob(job)}
                    disabled={savingJob === job.id}
                  >
                    {savingJob === job.id ? "Запазване…" : "Запази"}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <div className="grid gap-4">
        {sources.map((source) => (
          <section key={source.id} className="card overflow-hidden">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-edge/60 p-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-semibold text-white">{source.name}</h2>
                  <Badge tone={sourceStatusTone(source.status)}>{statusLabel(source.status)}</Badge>
                  <Badge tone={source.enabled ? "success" : "neutral"}>
                    {source.enabled ? "включен" : "изключен"}
                  </Badge>
                  {source.last_health_status && (
                    <Badge tone={source.last_health_status === "ok" ? "success" : "warning"}>
                      health: {source.last_health_status}
                    </Badge>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                  <a href={source.base_url} target="_blank" rel="noreferrer" className="hover:text-accent">
                    {source.base_url}
                  </a>
                  {source.robots_url && (
                    <a href={source.robots_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-accent">
                      robots.txt <ExternalLink size={11} />
                    </a>
                  )}
                  {source.terms_url && (
                    <a href={source.terms_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-accent">
                      условия <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500">{formatNumber(source.listing_count)} обяви</span>
                <button
                  className={`btn-ghost px-3 py-1.5 text-xs ${source.enabled ? "text-emerald-300" : ""}`}
                  onClick={() => void toggle(source)}
                  disabled={source.status !== "verified"}
                  title={source.status !== "verified" ? "Изисква потвърден разрешен достъп" : undefined}
                >
                  {source.enabled ? "Изключи" : "Включи"}
                </button>
                <button
                  className="btn-ghost px-3 py-1.5 text-xs"
                  onClick={() => void checkHealth(source)}
                  disabled={healthChecking === source.id}
                >
                  <Activity size={14} />
                  {healthChecking === source.id ? "Проверка…" : "Провери"}
                </button>
                <button
                  className="btn-ghost px-3 py-1.5 text-xs"
                  onClick={() => (editing === source.id ? setEditing(null) : startEdit(source))}
                >
                  <Settings2 size={14} /> Настройки
                  {editing === source.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
              </div>
            </div>

            <div className="grid gap-4 p-4 lg:grid-cols-[1.4fr_1fr]">
              <div>
                {source.notes && <p className="text-sm leading-relaxed text-slate-400">{source.notes}</p>}
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
                  <span className="rounded-lg bg-ink/50 px-2 py-1">
                    scraping: {String(source.capabilities.scraping ?? false)}
                  </span>
                  <span className="rounded-lg bg-ink/50 px-2 py-1">
                    images: {String(source.capabilities.images ?? false)}
                  </span>
                  <span className="rounded-lg bg-ink/50 px-2 py-1">
                    archives: {String(source.capabilities.archives ?? false)}
                  </span>
                  <span className="rounded-lg bg-ink/50 px-2 py-1">
                    проверен: {source.last_health_checked_at ? formatDate(source.last_health_checked_at) : "—"}
                  </span>
                </div>
              </div>

              {editing === source.id && draft ? (
                <div className="space-y-3 rounded-xl border border-edge/60 bg-ink/30 p-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="label">Страници / run</label>
                      <input
                        className="input"
                        type="number"
                        min={1}
                        max={50}
                        value={draft.max_pages_per_run}
                        onChange={(event) => setDraft({ ...draft, max_pages_per_run: event.target.value })}
                      />
                    </div>
                    <div>
                      <label className="label">Обяви / run</label>
                      <input
                        className="input"
                        type="number"
                        min={1}
                        max={200}
                        value={draft.max_listings_per_run}
                        onChange={(event) => setDraft({ ...draft, max_listings_per_run: event.target.value })}
                      />
                    </div>
                    <div>
                      <label className="label">Заявки / сек</label>
                      <input
                        className="input"
                        type="number"
                        step="0.1"
                        min={0.1}
                        max={5}
                        value={draft.requests_per_second}
                        onChange={(event) => setDraft({ ...draft, requests_per_second: event.target.value })}
                      />
                    </div>
                    <div>
                      <label className="label">Паралелни заявки</label>
                      <input
                        className="input"
                        type="number"
                        min={1}
                        max={4}
                        value={draft.max_concurrency}
                        onChange={(event) => setDraft({ ...draft, max_concurrency: event.target.value })}
                      />
                    </div>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={draft.download_images}
                      onChange={(event) => setDraft({ ...draft, download_images: event.target.checked })}
                    />
                    Изтегляй снимки в object storage
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={draft.archive_html}
                      onChange={(event) => setDraft({ ...draft, archive_html: event.target.checked })}
                    />
                    Архивирай HTML и screenshot (Playwright)
                  </label>
                  <button className="btn-primary w-full text-xs" onClick={() => void saveConfig(source)} disabled={saving}>
                    {saving ? "Запазване…" : "Запази настройките"}
                  </button>
                </div>
              ) : (
                <div className="rounded-xl border border-edge/60 bg-ink/30 p-3 text-xs text-slate-400">
                  <p className="mb-2 font-semibold text-slate-300">Текущи лимити</p>
                  <div className="grid grid-cols-2 gap-2">
                    <span>Страници: {String(source.config.max_pages_per_run ?? "—")}</span>
                    <span>Обяви: {String(source.config.max_listings_per_run ?? "—")}</span>
                    <span>RPS: {String(source.config.requests_per_second ?? "—")}</span>
                    <span>Паралелни: {String(source.config.max_concurrency ?? 1)}</span>
                    <span>Снимки: {String(source.config.download_images ?? false)}</span>
                    <span>Архив: {String(source.config.archive_html ?? false)}</span>
                  </div>
                </div>
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
