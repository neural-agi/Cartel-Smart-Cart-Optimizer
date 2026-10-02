"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/apiClient";
import { clearAuthState, setCsrfToken } from "@/lib/authSession";

function safeNextPath(): string {
  const candidate = new URLSearchParams(window.location.search).get("next");
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//") || candidate.includes("\\")) return "/home";
  return candidate;
}

export default function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
      const payload = (await response.json()) as { detail?: { message?: string }; csrf_token?: unknown };
      if (!response.ok) throw new Error(payload.detail?.message ?? "Unable to sign in with these credentials.");
      if (typeof payload.csrf_token === "string") setCsrfToken(payload.csrf_token);
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
      <section className="w-full max-w-md border-y border-border py-8 sm:border sm:px-8">
        <Link href="/" className="text-xl font-bold text-foreground">Cartel</Link>
        <p className="mt-8 text-sm font-medium text-primary">Your account</p>
        <h1 className="mt-2 text-2xl font-semibold">Sign in to Cartel</h1>
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
        <div className="mt-5 flex justify-between text-sm">
          <Link className="underline underline-offset-4" href="/signup">Create account</Link>
          <Link className="underline underline-offset-4" href="/recover">Forgot password?</Link>
        </div>
      </section>
    </main>
  );
}
