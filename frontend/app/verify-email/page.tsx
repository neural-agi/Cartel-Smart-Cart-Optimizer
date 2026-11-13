"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, readApiPayload, safeApiError } from "@/lib/apiClient";
import { setCsrfToken } from "@/lib/authSession";
import { useHashToken } from "@/lib/useHashToken";
import CartelMark from "@/components/brand/CartelMark";

export default function VerifyEmailPage() {
  const router = useRouter();
  const token = useHashToken();
  const [message, setMessage] = useState("Verifying your email…");
  useEffect(() => {
    if (!token) return;
    void apiFetch("/api/v2/auth/email/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) })
      .then(async (response) => {
        const body = await readApiPayload<{ csrf_token?: unknown }>(response);
        if (!response.ok || typeof body?.csrf_token !== "string") throw new Error(safeApiError(response, "This verification link is invalid or expired."));
        setCsrfToken(body.csrf_token); setMessage("Email verified. Opening your account…"); router.replace("/home");
      }).catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Verification failed."));
  }, [router, token]);
  return <main className="grid min-h-screen place-items-center bg-background px-4 py-12"><section className="min-w-0 w-full max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card p-6 text-center shadow-sm sm:max-w-md sm:p-9"><CartelMark href="/" /><p className="mt-8 text-sm leading-6 text-muted-foreground" role="status">{token ? message : "This verification link is incomplete."}</p></section></main>;
}
