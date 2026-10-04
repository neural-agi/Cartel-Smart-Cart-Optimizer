"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Loader2, ShoppingCart } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { optimizeCart } from "@/services/automaticPlanning";
import { useCartStore } from "@/store/cartStore";
import { consumerOptimizations } from "@/services/consumerOptimizations";
import { shoppingListsService } from "@/services/shoppingLists";
import type { ConsumerOptimizationResult } from "@/types/consumerOptimization";
import PageHeader from "@/components/consumer/PageHeader";
import Link from "next/link";
import { consumerReasons } from "@/lib/consumerCopy";

type SelectedAllocation = {
  item_id: string;
  quantity: number;
  retailer_id: string;
  checkout_group_id: string;
  listing_provenance: {
    platform: string;
    platform_listing_id: string;
    observation_id: string;
    observed_selling_price: { currency: string; minor_units: number };
  };
};

function selectedAllocations(result: ConsumerOptimizationResult): readonly SelectedAllocation[] {
  const chosen = result.optimizer_result?.chosen_plan as { candidate_item_allocations?: unknown } | undefined;
  return Array.isArray(chosen?.candidate_item_allocations)
    ? chosen.candidate_item_allocations as SelectedAllocation[]
    : [];
}

function money(currency: string, minorUnits: number) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(minorUnits / 100);
}

export default function OptimizePage() {
  const router = useRouter();
  const items = useCartStore((state) => state.items);
  const setAutomaticPlanning = useCartStore((state) => state.setAutomaticPlanning);
  const [consumerContext, setConsumerContext] = useState<{ listId: string; revision: number; requestId?: string } | null>(null);
  const [consumerResult, setConsumerResult] = useState<ConsumerOptimizationResult | null>(null);
  const [currentListRevision, setCurrentListRevision] = useState<number | null>(null);
  const [routeChecked, setRouteChecked] = useState(false);
  const [consumerLoading, setConsumerLoading] = useState(false);
  const [consumerError, setConsumerError] = useState<string | null>(null);
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const listId = query.get("list_id");
    const revision = Number(query.get("revision"));
    if (!listId) {
      setTimeout(() => setRouteChecked(true), 0);
      return;
    }
    const requestId = query.get("request_id") ?? undefined;
    const timer = window.setTimeout(() => {
      setConsumerContext({ listId, revision, requestId });
      setRouteChecked(true);
      if (!Number.isInteger(revision) || revision < 1) {
        setConsumerError("The list revision in this link is invalid. Return to your shopping list and try again.");
        return;
      }
      setConsumerLoading(Boolean(requestId));
      void shoppingListsService.get(listId).then((list) => setCurrentListRevision(list.revision))
        .catch(() => setCurrentListRevision(null));
      if (requestId) void consumerOptimizations.get(requestId).then((result) => {
        if (result.list_id !== listId || result.list_revision !== revision) {
          throw new Error("This saved optimization does not match the list revision in the URL.");
        }
        setConsumerResult(result);
      })
        .catch((cause: unknown) => setConsumerError(cause instanceof Error ? cause.message : "Saved result is unavailable."))
        .finally(() => setConsumerLoading(false));
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const mutation = useMutation({
    mutationFn: () => optimizeCart(items),
    onSuccess: (result) => {
      setAutomaticPlanning(result);
      if (
        result.status === "ready" &&
        result.optimization_result?.outcome === "selected"
      ) {
        router.push("/results");
      }
    },
  });

  async function optimizePersistedList() {
    if (!consumerContext || consumerLoading) return;
    setConsumerLoading(true); setConsumerError(null);
    try {
      const result = await consumerOptimizations.create(consumerContext.listId, consumerContext.revision);
      setConsumerResult(result);
      setCurrentListRevision(result.list_revision);
      setConsumerContext({ ...consumerContext, requestId: result.request_id });
      const query = new URLSearchParams(window.location.search);
      query.set("request_id", result.request_id);
      window.history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);
    } catch (cause) {
      setConsumerError(cause instanceof Error ? cause.message : "Could not optimize this list revision.");
    } finally { setConsumerLoading(false); }
  }

  if (!routeChecked) return <AppShell><p role="status" className="text-sm text-muted-foreground">Loading optimization context…</p></AppShell>;

  if (consumerContext) {
    return <AppShell><div className="space-y-6">
      <PageHeader eyebrow="Shopping list optimization" title={`Comparison for list revision ${consumerResult?.list_revision ?? consumerContext.revision}`} description="Cartel compares verified retailer information. Observed product prices are not checkout totals; fees, discounts, and payable amounts remain unavailable without checkout information." action={<Link className="text-sm font-medium text-primary underline-offset-4 hover:underline" href={`/lists?list_id=${encodeURIComponent(consumerContext.listId)}`}>Back to list</Link>} />
      {consumerError && <p role="alert" className="text-sm text-destructive">{consumerError}</p>}
      {consumerLoading && <p role="status" className="text-sm text-muted-foreground">Loading the persisted optimization result…</p>}
      {!consumerResult && !consumerLoading && consumerContext.revision > 0 && <Button onClick={() => void optimizePersistedList()}>Optimize this revision</Button>}
      {consumerResult && <section className="space-y-5 border-y border-border py-5" aria-live="polite">
        <div><h2 className="font-semibold">{consumerResult.status === "ready" ? "A plan is ready to review" : consumerResult.status === "unresolved" ? "Some items need review" : consumerResult.status === "infeasible" ? "Cartel could not build a complete plan" : consumerResult.status === "no_plan" ? "No plan is available yet" : "Comparison unavailable"}</h2><p className="mt-1 text-sm text-muted-foreground">{consumerResult.explanation}</p><p className="mt-2 text-xs text-muted-foreground">This comparison describes list revision {consumerResult.list_revision}; changes to the list require a new comparison.</p></div>
        {currentListRevision === null ? <p role="status" className="text-xs text-muted-foreground">Current list revision could not be checked; this result is only guaranteed to describe revision {consumerResult.list_revision}.</p> : currentListRevision !== consumerResult.list_revision ? <p role="status" className="text-sm text-amber-700">Historical result for revision {consumerResult.list_revision}. The list is now revision {currentListRevision}; optimize the current revision for an updated result.</p> : null}
        <div><h3 className="text-sm font-medium">What you asked for</h3><ul className="mt-2 divide-y divide-border border-y border-border">{consumerResult.requested_items.map((item) => <li key={item.item_id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><span>{item.query} × {item.quantity}</span><span className="text-muted-foreground">{item.resolution_status === "exact_confirmed" ? "Exact product confirmed" : "Product identity unresolved"}</span></li>)}</ul></div>
        {consumerResult.unresolved_items.length > 0 && <p className="text-sm text-amber-700">{consumerResult.unresolved_items.length} item(s) do not have a current, exact retailer offer and are not covered by this comparison.</p>}
        {consumerResult.status === "ready" && <div><h3 className="text-sm font-medium">Selected retailer groups</h3><p className="mt-1 text-xs text-muted-foreground">Retailers used: {new Set(selectedAllocations(consumerResult).map((allocation) => allocation.retailer_id)).size}</p><ul className="mt-2 divide-y divide-border border-y border-border">{selectedAllocations(consumerResult).map((allocation) => <li key={`${allocation.item_id}:${allocation.listing_provenance.observation_id}`} className="py-3 text-sm"><p>{consumerResult.requested_items.find((item) => item.item_id === allocation.item_id)?.query} × {allocation.quantity} · {allocation.retailer_id} ({allocation.listing_provenance.platform})</p><p className="text-xs text-muted-foreground">Observed unit price {money(allocation.listing_provenance.observed_selling_price.currency, allocation.listing_provenance.observed_selling_price.minor_units)}</p></li>)}</ul></div>}
        <div><h3 className="text-sm font-medium">Current retailer information</h3>{consumerResult.offers.length === 0 ? <p className="mt-2 text-sm text-muted-foreground">No current retailer offers are available for this list revision.</p> : <ul className="mt-2 divide-y divide-border border-y border-border">{consumerResult.offers.map((offer) => <li key={`${offer.item_id}:${offer.platform}:${offer.platform_listing_id}:${offer.observation_id}`} className="space-y-1 py-3 text-sm"><p>{consumerResult.requested_items.find((item) => item.item_id === offer.item_id)?.query} · {offer.platform} · quantity {offer.quantity}</p><p>Observed unit price {money(offer.observed_unit_price.currency, offer.observed_unit_price.minor_units)} · observed product subtotal {money(offer.observed_product_subtotal.currency, offer.observed_product_subtotal.minor_units)}</p><p className="text-xs text-muted-foreground">Captured {new Date(offer.observed_at).toLocaleString()}</p></li>)}</ul>}</div>
        <p className="text-xs text-muted-foreground">Observed product subtotal excludes delivery, handling, platform fees, discounts, and checkout changes. No savings or payable total is asserted.</p>
        {consumerResult.optimizer_result && <p className="text-xs text-muted-foreground">This is a saved comparison, not user approval, checkout readiness, or an order instruction.</p>}
      </section>}
    </div></AppShell>;
  }

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader eyebrow="Cart preparation" title="See how your cart could be bought." description="Cartel uses your exact list and verified retailer information to compare supported purchase paths. Optimization is a plan, not checkout or payment." />

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
              {mutation.data?.status === "unresolved" && (
                <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
                  <p className="font-medium">
                    {mutation.data.optimization_result?.outcome === "infeasible"
                      ? "No feasible plan is available."
                      : "Cartel could not select a plan from the available evidence."}
                  </p>
                  {mutation.data.unresolved_reasons.length > 0 && (
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
                      {consumerReasons(mutation.data.unresolved_reasons).map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  )}
                </div>
              )}
              {mutation.data?.status === "unavailable" && (
                <div role="status" className="rounded-xl border border-orange-500/30 bg-orange-500/5 p-4 text-sm">
                  <p className="font-medium">Checkout evidence is unavailable.</p>
                  <p className="mt-1 text-muted-foreground">No checkout total or effective cost was estimated.</p>
                  {mutation.data.unresolved_reasons.length > 0 && (
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
                      {consumerReasons(mutation.data.unresolved_reasons).map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  )}
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
