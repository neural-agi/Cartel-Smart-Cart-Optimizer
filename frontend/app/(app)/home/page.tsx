import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Search,
  ShoppingCart,
  Sparkles,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";

const actions = [
  {
    href: "/search",
    label: "Search products",
    description: "Find groceries to add to your cart.",
    icon: Search,
  },
  {
    href: "/cart",
    label: "View your cart",
    description: "Review the items you are considering.",
    icon: ShoppingCart,
  },
  {
    href: "/optimize",
    label: "Optimize your cart",
    description: "Compare the available ways to buy it.",
    icon: Sparkles,
  },
];

export default function HomePage() {
  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Your workspace</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Build a smarter cart.</h1>
          <p className="max-w-2xl text-muted-foreground">
            Start with the groceries you need. Cartel will be ready to compare them when product data is connected.
          </p>
        </header>

        <section aria-labelledby="quick-actions-heading" className="space-y-4">
          <div>
            <h2 id="quick-actions-heading" className="text-lg font-semibold tracking-tight">
              Get started
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">Choose where you want to begin.</p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {actions.map((action) => {
              const Icon = action.icon;

              return (
                <Link
                  key={action.href}
                  href={action.href}
                  className="group rounded-2xl border border-border bg-card p-5 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" aria-hidden="true" />
                  </div>
                  <h3 className="mt-5 font-semibold">{action.label}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{action.description}</p>
                </Link>
              );
            })}
          </div>
        </section>

        <section aria-labelledby="activity-heading" className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
              <BarChart3 className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="activity-heading" className="font-semibold">Recent activity</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Your recent carts and optimization results will appear here once activity is available.
              </p>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
