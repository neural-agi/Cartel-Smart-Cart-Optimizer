import { BarChart3, CalendarRange, Sparkles } from "lucide-react";

import AppShell from "@/components/layout/AppShell";

export default function WrappedPage() {
  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Cartel Wrapped</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Your grocery story, when it is ready.</h1>
          <p className="max-w-2xl text-muted-foreground">
            A future view of your shopping patterns, optimization history, and the choices you make over time.
          </p>
        </header>

        <section className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-20 text-center">
          <Sparkles className="mx-auto h-9 w-9 text-muted-foreground/60" aria-hidden="true" />
          <h2 className="mt-5 text-lg font-semibold">Your insights are not available yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">
            Wrapped will stay empty until real purchase history and optimization results can be collected and represented safely.
          </p>
        </section>

        <section aria-labelledby="insights-heading" className="grid gap-4 sm:grid-cols-2">
          <h2 id="insights-heading" className="sr-only">Future insight areas</h2>
          {[
            [CalendarRange, "Shopping history", "A timeline of your recorded grocery activity."],
            [BarChart3, "Optimization patterns", "A clear view of decisions supported by real results."],
          ].map(([Icon, title, description]) => {
            const InsightIcon = Icon as typeof CalendarRange;
            return (
              <div key={title as string} className="rounded-2xl border border-border bg-card p-5">
                <InsightIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <h3 className="mt-4 font-semibold">{title as string}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{description as string}</p>
              </div>
            );
          })}
        </section>
      </div>
    </AppShell>
  );
}
