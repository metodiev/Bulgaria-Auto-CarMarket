import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  Car,
  Copy,
  Database,
  KeyRound,
  LayoutDashboard,
  ListChecks,
  Menu,
  Sparkles,
  X,
} from "lucide-react";
import { getAdminKey, setAdminKey } from "../api/client";

const navigation = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/listings", label: "Обяви", icon: Car },
  { to: "/sources", label: "Източници", icon: Database },
  { to: "/scrape-runs", label: "Scraping", icon: ListChecks },
  { to: "/dedup", label: "Дубликати", icon: Copy },
  { to: "/errors", label: "Грешки", icon: AlertTriangle },
  { to: "/ai/settings", label: "AI настройки", icon: Sparkles },
  { to: "/ai/results", label: "AI анализи", icon: Bot },
];

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/listings": "Автомобилни обяви",
  "/sources": "Източници",
  "/scrape-runs": "Scraping задачи",
  "/dedup": "Дубликати",
  "/errors": "Грешки и логове",
  "/ai/settings": "AI настройки",
  "/ai/results": "AI анализи",
};

export default function Layout() {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState(getAdminKey());
  const location = useLocation();
  const title =
    pageTitles[location.pathname] ??
    (location.pathname.startsWith("/listings/")
      ? "Детайли за обява"
      : location.pathname.startsWith("/ai/results/")
        ? "AI резултат"
        : "Bulgaria Auto CarMarket");

  const saveKey = () => {
    setAdminKey(key.trim());
    setKey(key.trim());
  };

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-[260px] border-r border-edge/60 bg-ink/95 px-4 py-5 backdrop-blur transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-center justify-between">
          <NavLink to="/" className="flex items-center gap-3" onClick={() => setOpen(false)}>
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent/15 text-accent ring-1 ring-accent/30">
              <Car size={22} />
            </span>
            <span>
              <span className="block text-sm font-bold leading-tight text-white">Bulgaria Auto</span>
              <span className="block text-xs font-medium tracking-wide text-accent">CarMarket</span>
            </span>
          </NavLink>
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Затвори менюто">
            <X size={20} />
          </button>
        </div>

        <nav className="space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setOpen(false)}
                className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
              >
                <Icon size={17} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-8 rounded-xl border border-edge/60 bg-panel/60 p-3 text-xs leading-relaxed text-slate-400">
          <div className="mb-1 flex items-center gap-2 font-semibold text-slate-200">
            <KeyRound size={14} /> Admin ключ
          </div>
          Ключът се пази само в тази сесия и се изпраща като <code>X-Admin-Key</code>.
        </div>
      </aside>

      {open && (
        <button
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setOpen(false)}
          aria-label="Затвори"
        />
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-20 border-b border-edge/50 bg-ink/80 backdrop-blur">
          <div className="flex flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
            <button
              className="btn-ghost px-2.5 py-2 lg:hidden"
              onClick={() => setOpen(true)}
              aria-label="Отвори менюто"
            >
              <Menu size={18} />
            </button>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-lg font-semibold text-white">{title}</h1>
              <p className="hidden text-xs text-slate-500 sm:block">
                Self-hosted пазарни данни, история на цените и локален AI анализ
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="password"
                value={key}
                onChange={(event) => setKey(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") saveKey();
                }}
                placeholder="Admin API ключ"
                className="input w-44 py-1.5 text-xs sm:w-56"
                aria-label="Admin API ключ"
              />
              <button onClick={saveKey} className="btn-ghost px-3 py-1.5 text-xs">
                Запази
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
        <footer className="border-t border-edge/40 px-4 py-4 text-center text-xs text-slate-600 sm:px-6">
          Bulgaria Auto CarMarket · self-hosted · уважава правилата на източниците
        </footer>
      </div>
    </div>
  );
}
