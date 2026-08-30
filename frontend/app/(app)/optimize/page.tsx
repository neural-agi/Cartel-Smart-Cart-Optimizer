"use client";

import { useRouter } from "next/navigation";
import { AlertCircle, Loader2, ShoppingCart } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { optimizeCart } from "@/services/automaticPlanning";
import { useCartStore } from "@/store/cartStore";

export default function OptimizePage() {
  const router = useRouter();
  const items = useCartStore((state) => state.items);
  const setAutomaticPlanning = useCartStore((state) => state.setAutomaticPlanning);
  const mutation = useMutation({
    mutationFn: () => optimizeCart(items),
    onSuccess: (result) => {
      setAutomaticPlanning(result);
      router.push("/results");
    },
  });

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Cart preparation</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Check your cart data.</h1>
          <p className="max-w-2xl text-muted-foreground">Cartel will use your canonical cart to find governed candidates and compare supported ways to buy it.</p>
        </header>

        <section aria-labelledby="cart-context-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShoppingCart className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="cart-context-heading" className="font-semibold">Current cart context</h2>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {items.length === 0 ? "Add products before requesting an optimization." : `${items.length} item${items.length === 1 ? "" : "s"} ready for optimization.`}
              </p>
            </div>
          </div>

          {items.length === 0 ? (
            <div className="mt-8 rounded-xl border border-dashed border-border px-5 py-10 text-center">
              <p className="text-sm font-medium">No cart is ready</p>
                  <Button className="mt-5" onClick={() => router.push("/search")}>Search products</Button>
            </div>
          ) : (
            <div className="mt-8 space-y-4">
              {mutation.isPending && (
                  <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/30 p-4 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Building and evaluating candidate plans...
                </div>
              )}
              {mutation.isError && (
                <div role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
                  <span>{mutation.error instanceof Error ? mutation.error.message : "Optimization failed. Try again."}</span>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                  {mutation.isPending ? "Optimizing..." : "Optimize cart"}
                </Button>
              </div>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
