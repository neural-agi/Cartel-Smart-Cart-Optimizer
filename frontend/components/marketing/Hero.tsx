import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function Hero() {
  return (
    <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl items-center px-6 py-20">
      <div className="grid w-full items-center gap-16 lg:grid-cols-2">
        <div>
          <div className="mb-6 inline-flex rounded-full border border-border bg-muted px-4 py-2 text-sm text-muted-foreground">
            Save more. Shop smarter.
          </div>

          <h1 className="text-5xl font-bold leading-tight tracking-tight md:text-7xl">
            One Cart.
            <br />
            Every Grocery App.
            <br />
            Lowest Possible Price.
          </h1>

          <p className="mt-8 max-w-xl text-lg leading-8 text-muted-foreground">
            Compare prices across Blinkit, Zepto, Swiggy Instamart,
            BigBasket and more. Cartel automatically finds the cheapest
            combination for your entire grocery cart.
          </p>

          <div className="mt-10 flex flex-wrap gap-4">
            <Button size="lg">
              Get Early Access
            </Button>

            <Link
              href="https://github.com/neural-agi/Cartel-Smart-Cart-Optimizer"
              target="_blank"
            >
              <Button variant="outline" size="lg">
                GitHub
              </Button>
            </Link>
          </div>

          <p className="mt-8 text-sm text-muted-foreground">
            Built for people who are tired of paying different prices
            for the same groceries.
          </p>
        </div>

        <div className="flex items-center justify-center">
          <div className="flex h-[520px] w-full items-center justify-center rounded-3xl border border-border bg-muted/40">
            Product Mockup
          </div>
        </div>
      </div>
    </section>
  );
}