"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle2, CircleHelp } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { useCartStore } from "@/store/cartStore";

export default function ResultsPage() {
  const items = useCartStore((state) => state.items);
  const resolution = useCartStore((state) => state.resolution);

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Cart preparation result</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Resolved cart identities.</h1>
          <p className="max-w-2xl text-muted-foreground">This is a persisted data-resolution result. No cart optimization has run.</p>
        </header>

        {!resolution ? (
          <section className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-20 text-center">
            <CircleHelp className="mx-auto h-9 w-9 text-muted-foreground/60" aria-hidden="true" />
            <h2 className="mt-5 text-lg font-semibold">No resolution result yet</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">Resolve a populated cart first.</p>
            <Link href="/optimize" className="mt-6 inline-flex text-sm font-medium text-primary hover:underline">Prepare cart</Link>
          </section>
        ) : (
          <section aria-labelledby="resolved-items-heading" className="space-y-4">
            <h2 id="resolved-items-heading" className="text-lg font-semibold">Cart items</h2>
            <div className="divide-y divide-border rounded-2xl border border-border bg-card px-5">
              {resolution.items.map((item) => {
                const product = items.find((cartItem) => cartItem.itemId === item.item_id)?.product;
                const resolved = item.status === "resolved";
                return (
                  <article key={item.item_id} className="flex items-start justify-between gap-4 py-5">
                    <div className="min-w-0">
                      <h3 className="font-medium">{product?.name ?? item.item_id}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">Quantity: {item.quantity}</p>
                      {resolved ? (
                        <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                          <p>Product: {item.canonical_product_id}</p>
                          <p>Variant: {item.canonical_variant_id}</p>
                          {item.platform && <p>Listing: {item.platform} / {item.platform_listing_id}</p>}
                          {item.observation_id && <p>Observation: {item.observation_id}</p>}
                        </div>
                      ) : (
                        <p className="mt-3 text-sm text-destructive">{item.reason ?? "Item could not be resolved."}</p>
                      )}
                    </div>
                    <div className={`flex shrink-0 items-center gap-2 text-sm ${resolved ? "text-green-600" : "text-amber-600"}`}>
                      {resolved ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <AlertCircle className="h-4 w-4" aria-hidden="true" />}
                      {resolved ? "Resolved" : "Unresolved"}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}

        <Link href="/cart" className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to cart
        </Link>
      </div>
    </AppShell>
  );
}
