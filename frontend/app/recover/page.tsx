"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import CartelMark from "@/components/brand/CartelMark";

export default function RecoverPage() {
  const [email, setEmail] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    try { const response = await apiFetch("/api/v2/auth/password/recovery", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); if (!response.ok) throw new Error("Password recovery is temporarily unavailable."); setMessage("If this address has a verified Cartel account, recovery instructions will arrive shortly."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Request failed."); }
  }
  return <main className="grid min-h-screen place-items-center bg-background px-4 py-12"><section className="min-w-0 w-full max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card p-6 shadow-sm sm:max-w-md sm:p-9"><CartelMark href="/" /><h1 className="mt-8 text-2xl font-semibold">Recover your account</h1><p className="mt-2 text-sm text-muted-foreground">We will send instructions if this address has a verified Cartel account.</p><form onSubmit={submit} className="mt-7 space-y-4"><label htmlFor="recovery-email" className="text-sm font-medium">Email</label><Input id="recovery-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />{message && <p role="status" className="text-sm text-emerald-700">{message}</p>}{error && <p role="alert" className="text-sm text-destructive">{error}</p>}<Button className="w-full">Send recovery link</Button></form><Link className="mt-5 inline-flex text-sm text-primary hover:underline" href="/login">Back to sign in</Link></section></main>;
}
