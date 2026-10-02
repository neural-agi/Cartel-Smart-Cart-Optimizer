"use client";

import { useEffect, useState } from "react";
import { CircleUserRound, Mail, UserRound } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import { apiFetch } from "@/lib/apiClient";

interface ConsumerAccount { user_id: string; email: string; created_at: string }

export default function ProfilePage() {
  const [account, setAccount] = useState<ConsumerAccount | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void apiFetch("/api/v2/me", { cache: "no-store" }).then(async (response) => { if (!response.ok) throw new Error("Account details are unavailable."); setAccount(await response.json() as ConsumerAccount); }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : "Account details are unavailable.")); }, []);
  return <AppShell><div className="space-y-8">
    <header className="space-y-2"><p className="text-sm font-medium text-primary">Account</p><h1 className="text-3xl font-bold">Your account</h1><p className="text-muted-foreground">Account identity and sign-in details.</p></header>
    {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : !account ? <p role="status">Loading account…</p> : <>
      <section className="flex items-center gap-5 border-y border-border py-6"><CircleUserRound className="h-12 w-12 text-primary" aria-hidden="true"/><div><p className="font-semibold">Cartel account</p><p className="text-sm text-muted-foreground">{account.user_id}</p></div></section>
      <section className="grid gap-4 sm:grid-cols-2"><div className="border border-border p-4"><Mail className="h-4 w-4 text-muted-foreground" aria-hidden="true"/><p className="mt-3 text-xs text-muted-foreground">Verified email</p><p className="mt-1 text-sm font-medium">{account.email}</p></div><div className="border border-border p-4"><UserRound className="h-4 w-4 text-muted-foreground" aria-hidden="true"/><p className="mt-3 text-xs text-muted-foreground">User ID</p><p className="mt-1 break-all text-sm font-medium">{account.user_id}</p></div></section>
    </>}
  </div></AppShell>;
}
