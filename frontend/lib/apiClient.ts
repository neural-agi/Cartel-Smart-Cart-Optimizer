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

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const url = /^https?:\/\//i.test(path) ? path : `${API_BASE_URL}${path}`;
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  const requestUrl = new URL(url, typeof window === "undefined" ? "http://localhost" : window.location.origin);
  const isApi = requestUrl.pathname.startsWith("/api/v1/") || requestUrl.pathname.startsWith("/api/v2/");

  if (isApi && !SAFE_METHODS.has(method) && !PUBLIC_AUTH_PATHS.includes(requestUrl.pathname)) {
    let token = getCsrfToken();
    if (!token) {
      const csrfResponse = await fetch(`${API_BASE_URL}/api/v2/auth/csrf`, {
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

  const response = await fetch(url, {
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
