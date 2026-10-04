import { AUTH_REQUIRED_EVENT, clearAuthState, getCsrfToken, setCsrfToken } from "@/lib/authSession";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const PUBLIC_AUTH_PATHS = [
  "/api/v2/auth/signup",
  "/api/v2/auth/login",
  "/api/v2/auth/email/verify",
  "/api/v2/auth/verification/resend",
  "/api/v2/auth/password/recovery",
  "/api/v2/auth/password/reset",
];
const REQUEST_TIMEOUT_MS = 15_000;

export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `cartel-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export class ApiClientError extends Error {
  constructor(message = "Cartel could not reach the service. Try again shortly.") {
    super(message);
    this.name = "ApiClientError";
  }
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const abortSource = init.signal;
  const abort = () => controller.abort();
  abortSource?.addEventListener("abort", abort, { once: true });
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch {
    throw new ApiClientError();
  } finally {
    globalThis.clearTimeout(timeout);
    abortSource?.removeEventListener("abort", abort);
  }
}

export async function readApiPayload<T>(response: Response): Promise<T | null> {
  const body = await response.text();
  if (!body.trim()) return null;
  try {
    return JSON.parse(body) as T;
  } catch {
    return null;
  }
}

export function safeApiError(response: Response, fallback: string): string {
  if (response.status === 401) return "Your session or credentials could not be verified.";
  if (response.status === 403) return "This action is not available for the current account.";
  if (response.status === 404) return "That Cartel page or resource is not available.";
  if (response.status === 409) return "This change conflicts with the current saved state. Refresh and try again.";
  if (response.status === 422) return "Check the highlighted details and try again.";
  if (response.status === 429) return "Too many attempts. Wait a moment and try again.";
  if (response.status >= 500) return "Cartel could not reach the service. Check the local runtime and try again.";
  return fallback;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = /^https?:\/\//i.test(path) ? path : `${API_BASE_URL}${path}`;
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  const requestUrl = new URL(url, typeof window === "undefined" ? "http://localhost" : window.location.origin);
  const isApi = requestUrl.pathname.startsWith("/api/v1/") || requestUrl.pathname.startsWith("/api/v2/");

  if (isApi && !SAFE_METHODS.has(method) && !PUBLIC_AUTH_PATHS.includes(requestUrl.pathname)) {
    let token = getCsrfToken();
    if (!token) {
      const csrfResponse = await fetchWithTimeout(`${API_BASE_URL}/api/v2/auth/csrf`, {
        method: "GET",
        cache: "no-store",
        credentials: "same-origin",
      });
      if (csrfResponse.ok) {
        const payload = (await csrfResponse.json()) as { csrf_token?: unknown };
        if (typeof payload.csrf_token === "string") {
          token = payload.csrf_token;
          setCsrfToken(token);
        }
      }
    }
    if (token) headers.set("X-CSRF-Token", token);
  }

  const response = await fetchWithTimeout(url, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
  });
  const isPublicAuth = PUBLIC_AUTH_PATHS.includes(requestUrl.pathname);
  if (response.status === 401 && isApi && !isPublicAuth && typeof window !== "undefined") {
    clearAuthState();
    window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
  }
  return response;
}
