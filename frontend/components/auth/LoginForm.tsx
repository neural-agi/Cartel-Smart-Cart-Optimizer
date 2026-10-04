"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, readApiPayload, safeApiError } from "@/lib/apiClient";
import { clearAuthState, setCsrfToken } from "@/lib/authSession";
import CartelMark from "@/components/brand/CartelMark";

function safeNextPath(): string {
  const candidate = new URLSearchParams(window.location.search).get("next");
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//") || candidate.includes("\\")) return "/home";
  return candidate;
}

export default function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const code = new URLSearchParams(window.location.search).get("error");
    return {
      provider_cancelled: "Sign-in was cancelled. You can try again or use email and password.",
      account_link_required: "Sign in with your existing Cartel account before connecting this provider.",
      verified_email_required: "That provider did not confirm an email address for this account.",
      invalid_oauth_state: "This sign-in request expired. Start again.",
      provider_unavailable: "That sign-in option is not available right now.",
    }[code ?? ""] ?? null;
  });
  const [pending, setPending] = useState(false);
  const [providers, setProviders] = useState({ google: false, github: false, apple: false });

  useEffect(() => {
    void apiFetch("/api/v2/auth/providers", { cache: "no-store" })
      .then(async (response) => response.ok ? await response.json() as { providers?: typeof providers } : null)
      .then((payload) => { if (payload?.providers) setProviders((current) => ({ ...current, ...payload.providers })); })
      .catch(() => undefined);
  }, []);

  const configuredProviders = (["google", "github", "apple"] as const).filter((provider) => providers[provider]);
  const providerLabels = { google: "Google", github: "GitHub", apple: "Apple" };

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");
    setPending(true);
    setError(null);
    clearAuthState();
    try {
      const response = await apiFetch("/api/v2/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const payload = await readApiPayload<{ detail?: { message?: string }; csrf_token?: unknown }>(response);
      if (!response.ok) throw new Error(safeApiError(response, payload?.detail?.message ?? "Unable to sign in with these credentials."));
      if (typeof payload?.csrf_token === "string") setCsrfToken(payload.csrf_token);
      form.reset();
      router.replace(safeNextPath());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Cartel could not verify this session.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-background px-4 py-12">
      <section className="min-w-0 w-full max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card p-6 shadow-sm sm:max-w-md sm:p-9">
        <CartelMark href="/" />
        <p className="mt-8 text-sm font-medium text-primary">Your account</p>
        <h1 className="mt-2 text-2xl font-semibold">Sign in to Cartel</h1>
        {configuredProviders.length > 0 && <>
          <div className="mt-7 grid gap-2">
            {configuredProviders.map((provider) => <Button key={provider} type="button" variant="outline" className="w-full" disabled={pending} onClick={() => { router.push(`/api/v2/auth/${provider}/start?next=${encodeURIComponent(safeNextPath())}`); }}>
              Continue with {providerLabels[provider]}
            </Button>)}
          </div>
          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground"><span className="h-px flex-1 bg-border" /><span>or use email</span><span className="h-px flex-1 bg-border" /></div>
        </>}
        <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">Email</label>
            <Input id="email" name="email" type="email" autoComplete="email" required />
          </div>
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">Password</label>
            <Input id="password" name="password" type="password" autoComplete="current-password" required />
          </div>
          {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
          <Button className="h-10 w-full" type="submit" disabled={pending}>
            {pending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}
            {pending ? "Signing in…" : "Sign in"}
            {!pending ? <ArrowRight aria-hidden="true" /> : null}
          </Button>
        </form>
        <div className="mt-5 flex flex-wrap justify-between gap-x-4 gap-y-2 text-sm">
          <Link className="underline underline-offset-4" href="/signup">Create account</Link>
          <Link className="underline underline-offset-4" href="/recover">Forgot password?</Link>
        </div>
      </section>
    </main>
  );
}
