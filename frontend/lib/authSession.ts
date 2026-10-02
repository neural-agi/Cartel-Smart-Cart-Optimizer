let csrfToken: string | null = null;

export function getCsrfToken(): string | null {
  return csrfToken;
}

export function setCsrfToken(value: string): void {
  csrfToken = value;
}

export function clearAuthState(): void {
  csrfToken = null;
}

export const AUTH_REQUIRED_EVENT = "cartel:auth-required";
