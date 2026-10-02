"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/apiClient";
import { setCsrfToken } from "@/lib/authSession";
import { useHashToken } from "@/lib/useHashToken";

export default function VerifyEmailPage() {
  const router = useRouter();
  const token = useHashToken();
  const [message, setMessage] = useState("Verifying your email…");
  useEffect(() => {
    if (!token) return;
    void apiFetch("/api/v2/auth/email/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) })
      .then(async (response) => {
        const body = await response.json() as { csrf_token?: unknown };
        if (!response.ok || typeof body.csrf_token !== "string") throw new Error("This verification link is invalid or expired.");
        setCsrfToken(body.csrf_token); setMessage("Email verified. Opening your account…"); router.replace("/home");
      }).catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Verification failed."));
  }, [router, token]);
  return <main className="grid min-h-screen place-items-center px-6"><p role="status">{token ? message : "This verification link is incomplete."}</p></main>;
}
