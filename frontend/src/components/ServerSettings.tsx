import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, RefreshCw, Server, X } from "lucide-react";
import {
  getDefaultApiBase,
  getStoredApiBase,
  normalizeApiBase,
  setStoredApiBase,
} from "../api/server";

type Status = { kind: "ok" | "error"; text: string } | null;

export default function ServerSettings({
  open,
  onClose,
  required = false,
}: {
  open: boolean;
  onClose: () => void;
  required?: boolean;
}) {
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<Status>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (!open) return;
    const stored = getStoredApiBase();
    const fallback = getDefaultApiBase();
    setValue(stored || (fallback !== "/api" ? fallback : ""));
    setStatus(null);
  }, [open]);

  const normalized = useMemo(() => {
    if (!value.trim()) return "";
    try {
      return normalizeApiBase(value);
    } catch {
      return "";
    }
  }, [value]);

  if (!open) return null;

  const testConnection = async () => {
    setTesting(true);
    setStatus(null);
    try {
      const base = normalizeApiBase(value);
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 8000);
      let response: Response;
      try {
        response = await fetch(`${base}/health`, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
      } finally {
        window.clearTimeout(timeout);
      }
      const data = (await response.json().catch(() => null)) as
        | { database?: boolean; app?: string; version?: string }
        | null;
      if (!response.ok) {
        throw new Error(`Сървърът върна HTTP ${response.status}.`);
      }
      if (!data?.database) {
        throw new Error("API-то отговаря, но базата данни не е готова.");
      }
      setStatus({
        kind: "ok",
        text: `Връзката е успешна: ${data.app ?? "Bulgaria Auto CarMarket"}${
          data.version ? ` v${data.version}` : ""
        }.`,
      });
    } catch (error) {
      const message =
        error instanceof DOMException && error.name === "AbortError"
          ? "Изтече времето за връзка."
          : error instanceof Error
            ? error.message
            : "Неуспешна връзка.";
      setStatus({ kind: "error", text: message });
    } finally {
      setTesting(false);
    }
  };

  const save = () => {
    try {
      const base = normalizeApiBase(value);
      setStoredApiBase(base);
      window.location.reload();
    } catch (error) {
      setStatus({
        kind: "error",
        text: error instanceof Error ? error.message : "Невалиден адрес.",
      });
    }
  };

  const reset = () => {
    setStoredApiBase("");
    window.location.reload();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-3 backdrop-blur-sm sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="server-settings-title"
    >
      <div className="card w-full max-w-lg p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2
              id="server-settings-title"
              className="flex items-center gap-2 text-base font-semibold text-white"
            >
              <Server size={18} className="text-accent" /> Сървър на приложението
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">
              {required
                ? "Задайте адреса на вашия self-hosted backend, за да използвате мобилното приложение."
                : "Променете адреса на backend API. За уеб версията по подразбиране се използва относителен /api."}
            </p>
          </div>
          <button
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
            onClick={onClose}
            aria-label="Затвори"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-4">
          <label className="label" htmlFor="server-url">
            API адрес
          </label>
          <input
            id="server-url"
            className="input"
            inputMode="url"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            placeholder="http://192.168.1.10:8000/api"
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              setStatus(null);
            }}
          />
          <p className="mt-2 text-xs text-slate-500">
            Приема се и адрес без <code>/api</code> — той се добавя автоматично.
            {normalized && (
              <>
                {" "}
                Ще се използва: <span className="break-all text-accent">{normalized}</span>
              </>
            )}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            По подразбиране за уеб: <code>{getDefaultApiBase()}</code>. За препоръчване е
            HTTPS; HTTP е позволен за локална мрежа и разработка.
          </p>
        </div>

        {status && (
          <div
            className={`mt-3 flex items-start gap-2 rounded-xl border px-3 py-2 text-xs ${
              status.kind === "ok"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                : "border-rose-500/30 bg-rose-500/10 text-rose-200"
            }`}
          >
            {status.kind === "ok" && <CheckCircle2 size={15} className="mt-0.5 shrink-0" />}
            <span>{status.text}</span>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button className="btn-primary" onClick={save} disabled={!normalized}>
            Запази и презареди
          </button>
          <button className="btn-ghost" onClick={() => void testConnection()} disabled={testing || !normalized}>
            <RefreshCw size={15} className={testing ? "animate-spin" : ""} />
            {testing ? "Проверка…" : "Провери връзката"}
          </button>
          <button className="btn-ghost ml-auto px-3 py-1.5 text-xs" onClick={reset}>
            Изчисти
          </button>
        </div>
      </div>
    </div>
  );
}
