"use client";

import { useEffect, useState } from "react";
import { CircleUserRound, Mail } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { apiFetch } from "@/lib/apiClient";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";

interface ConsumerAccount { user_id: string; email: string; created_at: string }

export default function ProfilePage() {
  const [account, setAccount] = useState<ConsumerAccount | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void apiFetch("/api/v2/me", { cache: "no-store" }).then(async (response) => { if (!response.ok) throw new Error("Account details are unavailable."); setAccount(await response.json() as ConsumerAccount); }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Account details are unavailable.")); }, []);
  return <AppShell><div className="space-y-8">
    <PageHeader eyebrow="Account" title="Your account" description="Manage the account details Cartel currently supports." />
    {error ? <StatePanel icon={CircleUserRound} title="Account details unavailable" description="Cartel could not load your account right now. Return to this page and try again." tone="danger" /> : !account ? <p role="status" className="text-sm text-muted-foreground">Loading your account…</p> : <>
      <section className="surface-lift flex items-center gap-5 rounded-2xl border border-border bg-card p-6"><CircleUserRound className="h-12 w-12 text-primary" aria-hidden="true"/><div><p className="font-semibold">Cartel account</p><p className="text-sm text-muted-foreground">Signed in with your verified email.</p></div></section>
      <section className="rounded-2xl border border-border bg-card p-6"><Mail className="h-4 w-4 text-muted-foreground" aria-hidden="true"/><p className="mt-3 text-xs text-muted-foreground">Verified email</p><p className="mt-1 text-sm font-medium">{account.email}</p></section>
    </>}
  </div></AppShell>;
}
