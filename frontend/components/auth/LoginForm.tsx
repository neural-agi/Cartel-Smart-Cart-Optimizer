"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/apiClient";
import { setBearerToken } from "@/lib/authSession";

function safeNextPath(): string {
  const candidate = new URLSearchParams(window.location.search).get("next");
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//") || candidate.includes("\\")) {
    return "/home";
  }
  return candidate;
}

export default function LoginForm() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submittedToken = token.trim();
    if (!submittedToken) {
      setError("Enter the access token provided for this Cartel deployment.");
      return;
    }

    setPending(true);
    setError(null);
    try {
      const response = await apiFetch("/api/v1/auth/session", {
        method: "GET",
        cache: "no-store",
        bearerToken: submittedToken,
      });
      if (!response.ok) {
        throw new Error("That access token was not accepted.");
      }

      const session = (await response.json()) as { authenticated?: unknown };
      if (session.authenticated !== true) {
        throw new Error("Bearer authentication is not enabled for this API deployment.");
      }

      setBearerToken(submittedToken);
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
        <p className="mt-8 text-sm font-medium text-primary">Workspace access</p>
        <h1 className="mt-2 text-2xl font-semibold">Sign in to Cartel</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Use the bearer access token supplied by your deployment administrator. It stays in this browser tab.
        </p>

        <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label htmlFor="access-token" className="text-sm font-medium">Access token</label>
            <Input
              id="access-token"
              name="access-token"
              type="password"
              autoComplete="current-password"
              autoCapitalize="none"
              spellCheck={false}
              required
              value={token}
              onChange={(event) => setToken(event.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "login-error" : "token-help"}
              className="h-11"
            />
            <p id="token-help" className="text-xs text-muted-foreground">
              Your token is sent only to the Cartel API for verification and authenticated requests.
            </p>
          </div>

          {error && <p id="login-error" className="text-sm text-destructive" role="alert">{error}</p>}

          <Button className="h-10 w-full" type="submit" disabled={pending}>
            {pending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}
            {pending ? "Verifying access…" : "Continue"}
            {!pending ? <ArrowRight aria-hidden="true" /> : null}
          </Button>
        </form>

        <p className="mt-6 text-sm text-muted-foreground">
          Need access? <Link className="font-medium text-foreground underline underline-offset-4" href="/signup">Request an account</Link>
        </p>
      </section>
    </main>
  );
}
