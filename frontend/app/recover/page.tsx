"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RecoverPage() {
  const [email, setEmail] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    try { const response = await apiFetch("/api/v2/auth/password/recovery", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); if (!response.ok) throw new Error("Password recovery is temporarily unavailable."); setMessage("If this address has a verified Cartel account, recovery instructions will arrive shortly."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Request failed."); }
  }
  return <main className="grid min-h-screen place-items-center px-4"><section className="w-full max-w-md space-y-6"><Link href="/" className="text-xl font-bold">Cartel</Link><h1 className="text-2xl font-semibold">Recover your account</h1><form onSubmit={submit} className="space-y-4"><label htmlFor="recovery-email" className="text-sm">Email</label><Input id="recovery-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />{message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}<Button className="w-full">Send recovery link</Button></form></section></main>;
}
