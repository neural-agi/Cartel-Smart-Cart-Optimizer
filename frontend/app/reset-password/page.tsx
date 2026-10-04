"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useHashToken } from "@/lib/useHashToken";
import CartelMark from "@/components/brand/CartelMark";

export default function ResetPasswordPage() {
  const router = useRouter(); const token = useHashToken();
  const [password, setPassword] = useState(""); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    try { const response = await apiFetch("/api/v2/auth/password/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, new_password: password }) }); if (!response.ok) throw new Error("This recovery link is invalid or expired."); router.replace("/login"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Password reset failed."); }
  }
  return <main className="grid min-h-screen place-items-center bg-background px-4 py-12"><form onSubmit={submit} className="min-w-0 w-full max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card p-6 shadow-sm sm:max-w-md sm:p-9"><CartelMark href="/" /><h1 className="mt-8 text-2xl font-semibold">Choose a new password</h1><label className="mt-6 block space-y-2 text-sm font-medium" htmlFor="new-password"><span>New password</span><Input id="new-password" type="password" autoComplete="new-password" minLength={12} required value={password} onChange={(event) => setPassword(event.target.value)} /></label><p className="mt-2 text-xs text-muted-foreground">Use at least 12 characters.</p>{error && <p role="alert" className="mt-4 text-sm text-destructive">{error}</p>}<Button className="mt-6 w-full">Reset password</Button></form></main>;
}
