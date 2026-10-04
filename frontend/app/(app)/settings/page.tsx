"use client";

import { Monitor, Moon, Sun, Settings2 } from "lucide-react";
import { useTheme } from "next-themes";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";

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
        <PageHeader eyebrow="Preferences" title="Settings" description="Adjust the preferences currently supported by Cartel on this device." />

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

        <StatePanel icon={Settings2} title="More preferences are not available yet" description="Notifications, retailer preferences, and additional account controls will appear when Cartel can support them reliably." />
      </div>
    </AppShell>
  );
}
