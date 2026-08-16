"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, CheckCircle2, Loader2, ShoppingCart } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { CartResolutionError, resolveCart } from "@/services/cartResolution";
import {
  CartCandidateDiscoveryError,
  discoverCartCandidates,
} from "@/services/cartCandidates";
import { useCartStore } from "@/store/cartStore";

export default function OptimizePage() {
  const router = useRouter();
  const items = useCartStore((state) => state.items);
  const setResolution = useCartStore((state) => state.setResolution);
  const setCandidateDiscovery = useCartStore((state) => state.setCandidateDiscovery);
  const mutation = useMutation({
    mutationFn: async () => {
      const resolution = await resolveCart(items);
      const candidates = await discoverCartCandidates(resolution);
      return { resolution, candidates };
    },
    onSuccess: ({ resolution, candidates }) => {
      setResolution(resolution);
      setCandidateDiscovery(candidates);
      router.push("/results");
    },
  });
  const hasUnresolved = mutation.data?.resolution.items.some((item) => item.status === "unresolved") ?? false;

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Cart preparation</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Check your cart data.</h1>
          <p className="max-w-2xl text-muted-foreground">
            Cartel will resolve the saved product and listing identities before any comparison is attempted.
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
                {items.length === 0 ? "Add products before checking their persisted identities." : `${items.length} item${items.length === 1 ? "" : "s"} ready for resolution.`}
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
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Resolving persisted cart identities...
                </div>
              )}
              {mutation.isError && (
                <div role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
                  <span>{mutation.error instanceof CartResolutionError || mutation.error instanceof CartCandidateDiscoveryError ? mutation.error.message : "Cart preparation failed. Try again."}</span>
                </div>
              )}
              {mutation.isSuccess && !hasUnresolved && (
                <div className="flex items-center gap-3 rounded-xl border border-green-500/30 bg-green-500/5 p-4 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden="true" /> All cart items resolved.
                </div>
              )}
              {mutation.isSuccess && hasUnresolved && (
                <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
                  <AlertCircle className="h-4 w-4 text-amber-600" aria-hidden="true" /> Some cart items need attention.
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                  {mutation.isPending ? "Resolving..." : "Resolve cart identities"}
                </Button>
                <Link href="/cart" className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline">
                  Review cart <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
