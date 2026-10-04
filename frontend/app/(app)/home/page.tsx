import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Search,
  ShoppingCart,
  Sparkles,
} from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/consumer/PageHeader";
import MotionReveal from "@/components/consumer/MotionReveal";

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
        <PageHeader eyebrow="Your workspace" title="Tell Cartel what you need." description="Choose exact products, keep them in a list, and let Cartel compare only the retailer information it can verify." action={<Link className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/80 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50" href="/search">Start with search</Link>} />

        <section aria-labelledby="quick-actions-heading" className="space-y-4">
          <div><h2 id="quick-actions-heading" className="text-lg font-semibold tracking-tight">Start with your list</h2><p className="mt-1 text-sm text-muted-foreground">Search first when you want an exact verified product; use Lists to capture an item to review later.</p></div>

          <div className="grid gap-4 md:grid-cols-3">
            {actions.map((action, index) => {
              const Icon = action.icon;

              return (
                <MotionReveal key={action.href} delay={0.08 + index * 0.05}>
                  <Link
                    href={action.href}
                    className="group surface-lift block rounded-2xl border border-border bg-card p-5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
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
                </MotionReveal>
              );
            })}
          </div>
        </section>

        <section aria-labelledby="workflow-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
          <div className="max-w-xl">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">How Cartel works</p>
            <h2 id="workflow-heading" className="mt-2 text-xl font-semibold tracking-tight">One list. A clearer way to buy.</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">Cartel keeps your request, exact product choice, and comparison in one place. Missing retailer information stays visible instead of becoming a guess.</p>
          </div>
          <ol className="mt-7 grid gap-3 md:grid-cols-3">
            {["Tell us what you need", "Confirm the exact product", "Compare what is verifiable"].map((step, index) => (
              <li key={step} className="rounded-xl bg-muted/60 p-4">
                <span className="text-sm font-semibold text-primary">0{index + 1}</span>
                <p className="mt-4 font-medium">{step}</p>
              </li>
            ))}
          </ol>
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
