import { CircleUserRound, LockKeyhole, Mail, UserRound } from "lucide-react";

import AppShell from "@/components/layout/AppShell";

export default function ProfilePage() {
  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Account</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Your profile.</h1>
          <p className="max-w-2xl text-muted-foreground">Manage the account information associated with your Cartel workspace.</p>
        </header>

        <section className="flex flex-col gap-5 rounded-2xl border border-border bg-card p-6 sm:flex-row sm:items-center sm:p-8">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <CircleUserRound className="h-8 w-8" aria-hidden="true" />
          </div>
          <div>
            <p className="font-semibold">Authenticated profile</p>
            <p className="mt-1 text-sm text-muted-foreground">Profile identity will appear here when authentication is connected.</p>
          </div>
        </section>

        <section aria-labelledby="account-information-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
          <h2 id="account-information-heading" className="font-semibold">Account information</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {[
              [UserRound, "Name", "Not connected"],
              [Mail, "Email", "Not connected"],
              [LockKeyhole, "Sign-in method", "Not connected"],
            ].map(([Icon, label, value]) => {
              const AccountIcon = Icon as typeof UserRound;
              return (
                <div key={label as string} className="rounded-xl border border-border p-4">
                  <AccountIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  <p className="mt-3 text-xs text-muted-foreground">{label as string}</p>
                  <p className="mt-1 text-sm font-medium">{value as string}</p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
