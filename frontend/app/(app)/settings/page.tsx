"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";

const themes = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const mounted = typeof window !== "undefined";

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Preferences</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Settings.</h1>
          <p className="max-w-2xl text-muted-foreground">Adjust the preferences currently supported by the frontend.</p>
        </header>

        <section aria-labelledby="appearance-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
          <h2 id="appearance-heading" className="font-semibold">Appearance</h2>
          <p className="mt-1 text-sm text-muted-foreground">Choose how Cartel should appear on this device.</p>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {themes.map((item) => {
              const Icon = item.icon;
              const selected = mounted && theme === item.value;

              return (
                <Button
                  key={item.value}
                  type="button"
                  variant={selected ? "secondary" : "outline"}
                  className="h-auto justify-start gap-3 px-4 py-4"
                  aria-pressed={selected}
                  disabled={!mounted}
                  onClick={() => setTheme(item.value)}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Button>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-dashed border-border px-6 py-8">
          <h2 className="font-semibold">More settings will appear here</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Notifications, retailer preferences, and account controls are intentionally unavailable until their contracts and backend behavior exist.
          </p>
        </section>
      </div>
    </AppShell>
  );
}
