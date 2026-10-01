"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/apiClient";
import { AUTH_REQUIRED_EVENT, clearBearerToken, getBearerToken } from "@/lib/authSession";

interface AppAuthGuardProps {
  children: ReactNode;
}

export default function AppAuthGuard({ children }: AppAuthGuardProps) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    let active = true;
    const sendToLogin = () => {
      clearBearerToken();
      const next = `${window.location.pathname}${window.location.search}`;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    };
    const onAuthenticationRequired = () => sendToLogin();
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthenticationRequired);

    const token = getBearerToken();
    if (!token) {
      sendToLogin();
    } else {
      void apiFetch("/api/v1/auth/session", { cache: "no-store" })
        .then(async (response) => {
          if (!response.ok) return null;
          return (await response.json()) as { authenticated?: unknown; user_id?: unknown };
        })
        .then((session) => {
          if (!active) return;
          if (session?.authenticated === true && typeof session.user_id === "string") {
            setAuthenticated(true);
          } else {
            sendToLogin();
          }
        })
        .catch(() => {
          if (active) sendToLogin();
        });
    }

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
