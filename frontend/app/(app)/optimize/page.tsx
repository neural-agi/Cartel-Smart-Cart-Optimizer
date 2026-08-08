import Link from "next/link";
import { ArrowRight, CheckCircle2, ShoppingCart, Sparkles } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";

export default function OptimizePage() {
  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Optimization setup</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Ready to compare your cart?</h1>
          <p className="max-w-2xl text-muted-foreground">
            Cartel will compare represented product prices, offers, memberships, and fees before suggesting a practical way to buy.
          </p>
        </header>

        <section aria-labelledby="cart-context-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShoppingCart className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="cart-context-heading" className="font-semibold">Current cart context</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Your cart contents and governed cost context will appear here when they are available.
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-xl border border-dashed border-border px-5 py-10 text-center">
            <p className="text-sm font-medium">No cart is ready to optimize</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Add products before starting an optimization run.
            </p>
            <Button className="mt-5" disabled>Optimize cart</Button>
          </div>
        </section>

        <section aria-labelledby="comparison-heading" className="grid gap-4 md:grid-cols-3">
          {[
            ["Compare prices", "Review product-level prices across supported platforms."],
            ["Account for context", "Keep represented offers, fees, and membership benefits visible."],
            ["Choose a plan", "Present a recommended purchase plan when the data supports one."],
          ].map(([title, description], index) => (
            <div key={title} className="rounded-2xl border border-border bg-card p-5">
              <CheckCircle2 className="h-5 w-5 text-primary" aria-hidden="true" />
              <h2 id={index === 0 ? "comparison-heading" : undefined} className="mt-4 font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
            </div>
          ))}
        </section>

        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Link href="/cart" className="inline-flex items-center gap-2 font-medium text-primary hover:underline">
            Review cart <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link href="/results" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground">
            View results <Sparkles className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
