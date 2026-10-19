import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Cpu,
  Play,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
} from "lucide-react";
import { api, formatApiError, getAdminKey } from "../api/client";
import type { AIHealth, AIModelsResponse, AISettings as AISettingsType } from "../api/types";
import Badge from "../components/Badge";
import ErrorBox from "../components/ErrorBox";
import Loading from "../components/Loading";
import { formatDate } from "../lib/format";

const TASKS = [
  { value: "best_deals", label: "Най-изгодни сделки" },
  { value: "price_anomalies", label: "Ценови аномалии" },
  { value: "market_overview", label: "Пазарен преглед" },
];

export default function AISettings() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState<AISettingsType | null>(null);
  const [health, setHealth] = useState<AIHealth | null>(null);
  const [models, setModels] = useState<AIModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [taskType, setTaskType] = useState("best_deals");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [priceFrom, setPriceFrom] = useState("");
  const [priceTo, setPriceTo] = useState("");
  const [region, setRegion] = useState("");
  const [candidateLimit, setCandidateLimit] = useState("40");

  const load = async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setError(null);
    try {
      const [settingsData, healthData, modelsData] = await Promise.all([
        api<AISettingsType>("/ai/settings"),
        api<AIHealth>("/ai/health"),
        api<AIModelsResponse>("/ai/models"),
      ]);
      setSettings(settingsData);
      setHealth(healthData);
      setModels(modelsData);
      setTaskType(settingsData.default_task);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      if (showSpinner) setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const update = <K extends keyof AISettingsType>(key: K, value: AISettingsType[K]) => {
    setSettings((current) => (current ? { ...current, [key]: value } : current));
  };

  const save = async () => {
    if (!settings) return;
    if (!getAdminKey()) {
      setError("Въведете администраторски ключ в горната лента, за да променяте AI настройките.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await api<AISettingsType>("/ai/settings", {
        method: "PUT",
        body: JSON.stringify({
          enabled: settings.enabled,
          base_url: settings.base_url,
          model_name: settings.model_name,
          default_task: settings.default_task,
          auto_analyze: settings.auto_analyze,
          include_descriptions: settings.include_descriptions,
          analyze_images: false,
          max_concurrency: settings.max_concurrency,
          timeout_seconds: settings.timeout_seconds,
          max_attempts: settings.max_attempts,
        }),
      });
      setSettings(updated);
      await load(false);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setError(null);
    try {
      const [healthData, modelsData] = await Promise.all([
        api<AIHealth>("/ai/health"),
        api<AIModelsResponse>("/ai/models"),
      ]);
      setHealth(healthData);
      setModels(modelsData);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setTesting(false);
    }
  };

  const analyze = async () => {
    if (!getAdminKey()) {
      setError("Въведете администраторски ключ, за да стартирате AI анализ.");
      return;
    }
    setAnalyzing(true);
    setError(null);
    const filters: Record<string, string | number> = {};
    if (make) filters.make = make;
    if (model) filters.model = model;
    if (yearFrom) filters.year_from = Number(yearFrom);
    if (yearTo) filters.year_to = Number(yearTo);
    if (priceFrom) filters.price_from = Number(priceFrom);
    if (priceTo) filters.price_to = Number(priceTo);
    if (region) filters.region = region;
    try {
      const run = await api<{ id: string }>("/ai/analyze", {
        method: "POST",
        body: JSON.stringify({
          task_type: taskType,
          filters,
          candidate_limit: Number(candidateLimit) || 40,
        }),
      });
      navigate(`/ai/results/${run.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <Loading label="Зареждане на AI настройките…" />;
  if (!settings) return <ErrorBox message={error ?? "AI настройките не са налични."} onRetry={() => void load()} />;

  return (
    <div className="space-y-5">
      {error && <ErrorBox message={error} onRetry={() => void load()} />}

      <section className="card border-amber-500/20 bg-amber-500/[0.04] p-4 text-sm text-amber-100/90">
        <div className="flex items-start gap-3">
          <Sparkles className="mt-0.5 shrink-0 text-amber-300" size={18} />
          <div>
            <p className="font-semibold">AI модулът е напълно опционален.</p>
            <p className="mt-1 text-amber-100/70">
              При изключен AI всички scraping, филтри, история и статистики продължават да работят.
              Стартирайте AI услугите с{" "}
              <code className="rounded bg-black/30 px-1.5 py-0.5">docker compose --profile ai up -d --build</code>.
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
        <section className="card p-4">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
            <Server size={16} className="text-accent" /> Ollama конфигурация
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="label">Ollama Base URL</label>
              <input
                className="input"
                value={settings.base_url}
                onChange={(event) => update("base_url", event.target.value)}
              />
            </div>
            <div>
              <label className="label">Модел</label>
              <input
                className="input"
                list="ollama-models"
                value={settings.model_name}
                onChange={(event) => update("model_name", event.target.value)}
              />
              <datalist id="ollama-models">
                {models?.models.map((item) => (
                  <option key={item.name} value={item.name} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="label">Тип по подразбиране</label>
              <select
                className="input"
                value={settings.default_task}
                onChange={(event) => update("default_task", event.target.value)}
              >
                {TASKS.map((task) => (
                  <option key={task.value} value={task.value}>
                    {task.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Max concurrency</label>
              <input
                className="input"
                type="number"
                min={1}
                max={4}
                value={settings.max_concurrency}
                onChange={(event) => update("max_concurrency", Number(event.target.value))}
              />
            </div>
            <div>
              <label className="label">Timeout (сек)</label>
              <input
                className="input"
                type="number"
                min={10}
                max={600}
                value={settings.timeout_seconds}
                onChange={(event) => update("timeout_seconds", Number(event.target.value))}
              />
            </div>
            <div>
              <label className="label">Max опити</label>
              <input
                className="input"
                type="number"
                min={1}
                max={5}
                value={settings.max_attempts}
                onChange={(event) => update("max_attempts", Number(event.target.value))}
              />
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={settings.enabled}
                onChange={(event) => update("enabled", event.target.checked)}
              />
              AI модулът е включен
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={settings.auto_analyze}
                onChange={(event) => update("auto_analyze", event.target.checked)}
              />
              Автоматичен анализ след scraping
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={settings.include_descriptions}
                onChange={(event) => update("include_descriptions", event.target.checked)}
              />
              Включвай описанията на обявите
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-500">
              <input type="checkbox" checked={false} disabled />
              Анализ на снимки (изисква проверен vision модел — изключено за qwen3:4b)
            </label>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button className="btn-primary" onClick={() => void save()} disabled={saving}>
              {saving ? <RefreshCw className="animate-spin" size={16} /> : <ShieldCheck size={16} />}
              {saving ? "Запазване…" : "Запази настройките"}
            </button>
            <button className="btn-ghost" onClick={() => void testConnection()} disabled={testing}>
              <RefreshCw className={testing ? "animate-spin" : ""} size={16} /> Провери връзката
            </button>
          </div>
          {settings.updated_at && (
            <p className="mt-2 text-xs text-slate-500">Последна промяна: {formatDate(settings.updated_at)}</p>
          )}
        </section>

        <section className="space-y-5">
          <div className="card p-4">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
              <Cpu size={16} className="text-accent" /> Състояние на Ollama
            </h2>
            {health ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={health.reachable ? "success" : "danger"}>
                    {health.reachable ? "достъпен" : "недостъпен"}
                  </Badge>
                  <Badge tone={health.model_available ? "success" : "warning"}>
                    {health.model_available ? "моделът е наличен" : "моделът липсва"}
                  </Badge>
                  <Badge tone={health.enabled ? "success" : "neutral"}>
                    {health.enabled ? "AI включен" : "AI изключен"}
                  </Badge>
                </div>
                <p className="text-sm text-slate-300">{health.message}</p>
                {!health.model_available && (
                  <div className="rounded-xl border border-edge/60 bg-ink/40 p-3 text-xs text-slate-400">
                    <p className="mb-1 flex items-center gap-1 font-semibold text-slate-200">
                      <TerminalSquare size={13} /> Инсталиране на модела
                    </p>
                    <code className="block break-all text-accent">
                      docker compose exec ollama ollama pull {health.model || "qwen3:4b"}
                    </code>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-400">Няма данни.</p>
            )}
          </div>

          <div className="card p-4">
            <h2 className="mb-3 text-sm font-semibold text-white">Инсталирани модели</h2>
            {models?.reachable ? (
              models.models.length > 0 ? (
                <ul className="space-y-1 text-sm text-slate-300">
                  {models.models.map((item) => (
                    <li key={item.name} className="flex items-center justify-between gap-2 rounded-lg bg-ink/40 px-3 py-2">
                      <span className="truncate">{item.name}</span>
                      {item.size && <span className="text-xs text-slate-500">{(item.size / 1e9).toFixed(1)} GB</span>}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">Няма инсталирани модели.</p>
              )
            ) : (
              <p className="text-sm text-slate-400">{models?.error ?? "Ollama не е достъпен."}</p>
            )}
          </div>
        </section>
      </div>

      <section className="card p-4">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
          <Play size={16} className="text-accent" /> Ръчен AI анализ
        </h2>
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-4">
          <div>
            <label className="label">Тип анализ</label>
            <select className="input" value={taskType} onChange={(event) => setTaskType(event.target.value)}>
              {TASKS.map((task) => (
                <option key={task.value} value={task.value}>
                  {task.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Марка</label>
            <input className="input" placeholder="Audi" value={make} onChange={(event) => setMake(event.target.value)} />
          </div>
          <div>
            <label className="label">Модел</label>
            <input className="input" placeholder="A4" value={model} onChange={(event) => setModel(event.target.value)} />
          </div>
          <div>
            <label className="label">Регион</label>
            <input className="input" placeholder="София-град" value={region} onChange={(event) => setRegion(event.target.value)} />
          </div>
          <div>
            <label className="label">Година от</label>
            <input className="input" type="number" value={yearFrom} onChange={(event) => setYearFrom(event.target.value)} />
          </div>
          <div>
            <label className="label">Година до</label>
            <input className="input" type="number" value={yearTo} onChange={(event) => setYearTo(event.target.value)} />
          </div>
          <div>
            <label className="label">Цена от</label>
            <input className="input" type="number" value={priceFrom} onChange={(event) => setPriceFrom(event.target.value)} />
          </div>
          <div>
            <label className="label">Цена до</label>
            <input className="input" type="number" value={priceTo} onChange={(event) => setPriceTo(event.target.value)} />
          </div>
          <div>
            <label className="label">Кандидати към модела</label>
            <input
              className="input"
              type="number"
              min={5}
              max={100}
              value={candidateLimit}
              onChange={(event) => setCandidateLimit(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <button className="btn-primary w-full" onClick={() => void analyze()} disabled={analyzing || !settings.enabled}>
              {analyzing ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
              {analyzing ? "Стартиране…" : "Стартирай анализ"}
            </button>
          </div>
        </div>
        {!settings.enabled && (
          <p className="mt-2 text-xs text-amber-300">
            Включете AI модула и запазете настройките, преди да стартирате анализ.
          </p>
        )}
      </section>
    </div>
  );
}
