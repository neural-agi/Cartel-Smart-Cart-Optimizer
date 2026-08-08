import Link from "next/link";
import { ArrowLeft, BarChart3, CircleHelp, ShoppingCart } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";

export default function ResultsPage() {
  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Optimization results</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Your best way to buy.</h1>
          <p className="max-w-2xl text-muted-foreground">
            The recommendation will show the cart breakdown, platform allocation, and complete cost context here.
          </p>
        </header>

        <section className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-20 text-center">
          <BarChart3 className="mx-auto h-9 w-9 text-muted-foreground/60" aria-hidden="true" />
          <h2 className="mt-5 text-lg font-semibold">No optimization results yet</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">
            Run an optimization with a populated cart to see item prices, fees, platform allocation, totals, and savings when those values are available.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Button disabled>Start optimization</Button>
            <Button variant="outline" disabled>Compare another cart</Button>
          </div>
        </section>

        <section aria-labelledby="result-sections-heading" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <h2 id="result-sections-heading" className="sr-only">Result sections</h2>
          {["Recommended plan", "Cart allocation", "Cost breakdown", "Evidence"].map((label) => (
            <div key={label} className="rounded-2xl border border-border bg-card p-5">
              <CircleHelp className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
              <p className="mt-4 text-sm font-medium">{label}</p>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">Awaiting an available result.</p>
            </div>
          ))}
        </section>

        <Link href="/cart" className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to cart
        </Link>
      </div>
    </AppShell>
  );
}
