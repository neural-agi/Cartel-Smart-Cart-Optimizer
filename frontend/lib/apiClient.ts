import { AUTH_REQUIRED_EVENT, clearBearerToken, getBearerToken } from "@/lib/authSession";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export type ApiRequestInit = RequestInit & {
  bearerToken?: string | null;
};

function isVersionedApiRequest(url: string): boolean {
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  const requestUrl = new URL(url, origin);
  const apiOrigin = API_BASE_URL ? new URL(API_BASE_URL, origin).origin : origin;
  return requestUrl.origin === apiOrigin && requestUrl.pathname.startsWith("/api/v1/");
}

export async function apiFetch(path: string, init: ApiRequestInit = {}): Promise<Response> {
  const { bearerToken, ...requestInit } = init;
  const url = /^https?:\/\//i.test(path) ? path : `${API_BASE_URL}${path}`;
  const usesStoredToken = bearerToken === undefined;
  const token = usesStoredToken ? getBearerToken() : bearerToken;
  const headers = new Headers(requestInit.headers);

  if (token && isVersionedApiRequest(url)) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, { ...requestInit, headers });
  if (response.status === 401 && usesStoredToken && token && typeof window !== "undefined") {
    clearBearerToken();
    window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
  }
  return response;
}
