import { Capacitor } from "@capacitor/core";

const API_BASE_STORAGE = "carmarket.apiBase";
const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export function isNativeApp(): boolean {
  return Capacitor.isNativePlatform();
}

export function getDefaultApiBase(): string {
  return DEFAULT_API_BASE;
}

export function getStoredApiBase(): string {
  try {
    return localStorage.getItem(API_BASE_STORAGE) ?? "";
  } catch {
    return "";
  }
}

export function getApiBase(): string {
  return getStoredApiBase() || DEFAULT_API_BASE;
}

export function setStoredApiBase(value: string): void {
  if (value) {
    localStorage.setItem(API_BASE_STORAGE, value);
  } else {
    localStorage.removeItem(API_BASE_STORAGE);
  }
}

/**
 * Accepts `host:port`, `http://host:port`, or a full URL. The API prefix is
 * normalized to `/api`, so users can enter either the server root or the API URL.
 */
export function normalizeApiBase(input: string): string {
  let value = input.trim();
  if (!value) {
    throw new Error("Въведете адрес на сървъра.");
  }
  if (!/^https?:\/\//i.test(value)) {
    value = `http://${value}`;
  }

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("Невалиден URL адрес.");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("Адресът трябва да започва с http:// или https://.");
  }
  if (!url.hostname) {
    throw new Error("Адресът няма host.");
  }
  if (url.username || url.password) {
    throw new Error("Не използвайте потребител и парола в URL адреса.");
  }

  let path = url.pathname.replace(/\/+$/, "");
  if (!path) {
    path = "/api";
  } else if (!/\/api$/i.test(path)) {
    path = `${path}/api`;
  }
  return `${url.protocol}//${url.host}${path}`;
}

export function apiBaseLabel(value: string): string {
  if (!value) return "Сървърът не е зададен";
  try {
    return new URL(value).host;
  } catch {
    return value;
  }
}
