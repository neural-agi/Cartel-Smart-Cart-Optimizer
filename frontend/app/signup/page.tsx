"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { apiFetch, readApiPayload, safeApiError } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import CartelMark from "@/components/brand/CartelMark";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [showResend, setShowResend] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const submittedEmail = String(formData.get("email") ?? "");
    const submittedPassword = String(formData.get("password") ?? "");
    setEmail(submittedEmail); setPending(true); setError(""); setMessage("");
    try {
      const response = await apiFetch("/api/v2/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: submittedEmail, password: submittedPassword }) });
      const body = await readApiPayload<{ detail?: { code?: string } }>(response);
      if (!response.ok) throw new Error(body?.detail?.code === "email_delivery_unavailable" ? "Account email delivery is temporarily unavailable. Try again later." : safeApiError(response, "Cartel could not create this account request."));
      form.reset();
      setMessage("If this email can be verified, Cartel will send a link shortly.");
      setShowResend(true);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Request failed."); }
    finally { setPending(false); }
  }

  async function resend() {
    setPending(true); setError("");
    try {
      const response = await apiFetch("/api/v2/auth/verification/resend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) });
      if (!response.ok) throw new Error("Verification email delivery is temporarily unavailable.");
      setMessage("If this email has an unverified Cartel account, a new link will arrive shortly.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Request failed."); }
    finally { setPending(false); }
  }

  return <main className="grid min-h-screen place-items-center bg-background px-4 py-12"><section className="min-w-0 w-full max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card p-6 shadow-sm sm:max-w-md sm:p-9">
    <CartelMark href="/" /><h1 className="mt-8 text-2xl font-semibold">Create your account</h1>
    <form className="mt-7 space-y-5" onSubmit={submit}>
      <div className="space-y-2"><label htmlFor="signup-email" className="text-sm font-medium">Email</label><Input id="signup-email" name="email" type="email" autoComplete="email" required /></div>
      <div className="space-y-2"><label htmlFor="signup-password" className="text-sm font-medium">Password</label><Input id="signup-password" name="password" type="password" autoComplete="new-password" minLength={12} required /><p className="text-xs text-muted-foreground">Use at least 12 characters.</p></div>
      {message && <p role="status" className="text-sm">{message}</p>}{error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {showResend && <button type="button" className="text-sm underline underline-offset-4" disabled={pending} onClick={() => void resend()}>Resend verification email</button>}
      <Button className="w-full" type="submit" disabled={pending}>{pending ? "Creating account…" : "Create account"}</Button>
    </form><p className="mt-5 text-sm text-muted-foreground">Already have an account? <Link href="/login" className="underline">Sign in</Link></p>
  </section></main>;
}
