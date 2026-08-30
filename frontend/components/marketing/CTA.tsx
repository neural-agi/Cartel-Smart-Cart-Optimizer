import Link from "next/link";

import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function CTA() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24">
      <div className="overflow-hidden rounded-3xl border border-border bg-card">
        <div className="mx-auto flex max-w-5xl flex-col items-center px-8 py-20 text-center">
          <span className="rounded-full border border-primary/20 bg-primary/10 px-4 py-2 text-sm font-medium text-primary">
            Coming Soon
          </span>

          <h2 className="mt-8 max-w-3xl text-4xl font-bold tracking-tight md:text-5xl">
            Stop opening five grocery apps
            <br />
            just to save ₹100.
          </h2>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
            Cartel compares prices, delivery fees, memberships and offers
            across every major grocery platform so you don&apos;t have to.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Button size="lg">
              Join Early Access
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>

            <Link
              href="https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer"
              target="_blank"
            >
              <Button variant="outline" size="lg">
                View GitHub
              </Button>
            </Link>
          </div>

          <p className="mt-8 text-sm text-muted-foreground">
            Built for students, families, professionals and anyone tired of
            paying more than they should.
          </p>
        </div>
      </div>
    </section>
  );
}
