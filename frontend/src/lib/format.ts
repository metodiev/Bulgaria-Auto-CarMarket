export function formatPrice(value: number | null | undefined, currency?: string | null): string {
  if (value === null || value === undefined) return "по договаряне";
  const code = currency === "BGN" ? "BGN" : currency || "EUR";
  try {
    return new Intl.NumberFormat("bg-BG", {
      style: "currency",
      currency: code,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${Math.round(value).toLocaleString("bg-BG")} ${code}`;
  }
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("bg-BG").format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("bg-BG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDateShort(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("bg-BG", { dateStyle: "medium" }).format(date);
}

export function formatKm(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${formatNumber(value)} км`;
}

export function fuelLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    diesel: "Дизел",
    petrol: "Бензин",
    lpg: "Газ",
    lpg_petrol: "Газ/Бензин",
    cng: "Метан",
    electric: "Електрически",
    hybrid: "Хибрид",
    plug_in_hybrid: "Плъгин хибрид",
  };
  return value ? labels[value] ?? value : "—";
}

export function transmissionLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    automatic: "Автоматична",
    manual: "Ръчна",
    semi_automatic: "Полуавтоматична",
    cvt: "Вариатор",
  };
  return value ? labels[value] ?? value : "—";
}

export function bodyLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    estate: "Комби",
    sedan: "Седан",
    hatchback: "Хечбек",
    suv: "SUV",
    coupe: "Купе",
    convertible: "Кабриолет",
    van: "Ван",
    minivan: "Миниван",
    pickup: "Пикап",
  };
  return value ? labels[value] ?? value : "—";
}

export function driveLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    awd: "4x4",
    rwd: "Задно",
    fwd: "Предно",
  };
  return value ? labels[value] ?? value : "—";
}

export function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    pending: "Чака",
    running: "Изпълнява се",
    completed: "Завършен",
    failed: "Неуспешен",
    cancelled: "Отказан",
    active: "Активна",
    inactive: "Неактивна",
    duplicate: "Дубликат",
    resolved: "Решен",
    ignored: "Игнориран",
    verified: "Проверен",
    needs_permission: "Нужно разрешение",
    blocked: "Блокиран",
    disabled: "Изключен",
  };
  return labels[value] ?? value;
}

export function sourceStatusTone(value: string): "success" | "warning" | "danger" | "neutral" {
  if (value === "verified") return "success";
  if (value === "needs_permission") return "warning";
  if (value === "blocked") return "danger";
  return "neutral";
}

export function runStatusTone(value: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (value === "completed") return "success";
  if (value === "running") return "info";
  if (value === "pending") return "warning";
  if (value === "failed") return "danger";
  return "neutral";
}

export function taskLabel(value: string): string {
  const labels: Record<string, string> = {
    best_deals: "Най-изгодни сделки",
    price_anomalies: "Ценови аномалии",
    market_overview: "Пазарен преглед",
  };
  return labels[value] ?? value;
}
