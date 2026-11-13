"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/apiClient";
import { AUTH_REQUIRED_EVENT, clearAuthState, setCsrfToken } from "@/lib/authSession";

interface AppAuthGuardProps {
  children: ReactNode;
}

export default function AppAuthGuard({ children }: AppAuthGuardProps) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    let active = true;
    const sendToLogin = () => {
      clearAuthState();
      const next = `${window.location.pathname}${window.location.search}`;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    };
    const onAuthenticationRequired = () => sendToLogin();
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthenticationRequired);

    void apiFetch("/api/v2/me", { cache: "no-store" })
      .then(async (response) => response.ok ? await response.json() as { user_id?: unknown } : null)
      .then(async (me) => {
        if (!active) return;
        if (!me || typeof me.user_id !== "string") return sendToLogin();
        const csrfResponse = await fetch("/api/v2/auth/csrf", { cache: "no-store", credentials: "same-origin" });
        if (!csrfResponse.ok) return sendToLogin();
        const csrf = await csrfResponse.json() as { csrf_token?: unknown };
        if (typeof csrf.csrf_token !== "string") return sendToLogin();
        setCsrfToken(csrf.csrf_token);
        setAuthenticated(true);
      })
      .catch(() => { if (active) sendToLogin(); });

    return () => {
      active = false;
      window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthenticationRequired);
    };
  }, [router]);

  if (!authenticated) {
    return (
      <main className="grid min-h-screen place-items-center bg-background px-6" aria-busy="true">
        <p className="text-sm text-muted-foreground" role="status">Checking your Cartel session…</p>
      </main>
    );
  }

  return children;
}
