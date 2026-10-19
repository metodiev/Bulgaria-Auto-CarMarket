import { getApiBase, getStoredApiBase, isNativeApp } from "./server";

const ADMIN_KEY_STORAGE = "carmarket.adminKey";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getAdminKey(): string {
  return sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? "";
}

export function setAdminKey(value: string): void {
  if (value) {
    sessionStorage.setItem(ADMIN_KEY_STORAGE, value);
  } else {
    sessionStorage.removeItem(ADMIN_KEY_STORAGE);
  }
}

export function buildQuery(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    query.set(key, String(value));
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (isNativeApp() && !getStoredApiBase()) {
    throw new ApiError(
      0,
      "Адресът на сървъра не е зададен. Отворете „Сървър“ в горната лента и въведете URL.",
    );
  }

  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const adminKey = getAdminKey();
  if (adminKey) {
    headers.set("X-Admin-Key", adminKey);
  }

  let response: Response;
  try {
    response = await fetch(`${getApiBase()}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "Няма връзка със сървъра. Проверете адреса, мрежата и дали backend-ът работи.",
    );
  }
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") message = data.detail;
      else if (data.detail) message = JSON.stringify(data.detail);
    } catch {
      // Keep the status-based message.
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Невалиден или липсващ администраторски ключ.";
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Неочаквана грешка.";
}
