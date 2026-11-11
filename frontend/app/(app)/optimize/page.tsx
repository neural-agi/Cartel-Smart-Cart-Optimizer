"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2, ShoppingCart } from "lucide-react";
import Link from "next/link";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { consumerOptimizations } from "@/services/consumerOptimizations";
import { shoppingListsService } from "@/services/shoppingLists";
import type { ConsumerOptimizationResult } from "@/types/consumerOptimization";
import type { ShoppingList } from "@/types/shoppingLists";
import PageHeader from "@/components/consumer/PageHeader";
import OptimizationStatusGuide from "@/components/consumer/OptimizationStatusGuide";

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

function evidenceLabel(evidenceClass: string): string | null {
  if (evidenceClass === "synthetic_demo") return "Synthetic demo";
  if (evidenceClass === "demo_fixture") return "Demo fixture";
  if (evidenceClass === "policy_blocked") return "Blocked retailer";
  return null;
}

export default function OptimizePage() {
  const [lists, setLists] = useState<readonly ShoppingList[]>([]);
  const [listsLoading, setListsLoading] = useState(true);
  const [listsError, setListsError] = useState<string | null>(null);
  const [selectedListId, setSelectedListId] = useState("");
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
    const requestId = query.get("request_id") ?? undefined;
    if (!listId) {
      let mounted = true;
      void shoppingListsService.list().then((result) => {
        if (!mounted) return;
        setLists(result);
        const first = result.find((list) => !list.archived && list.items.length > 0)
          ?? result.find((list) => !list.archived);
        setSelectedListId(first?.id ?? "");
      }).catch((error: unknown) => {
        if (mounted) setListsError(error instanceof Error ? error.message : "Shopping lists are unavailable.");
      }).finally(() => {
        if (mounted) setListsLoading(false);
      });
      setRouteChecked(true);
      return () => { mounted = false; };
    }
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
  }, []);

  async function startOptimization(listId: string, revision: number) {
    if (consumerLoading) return;
    setConsumerLoading(true);
    setConsumerError(null);
    try {
      const result = await consumerOptimizations.create(listId, revision);
      setConsumerResult(result);
      setCurrentListRevision(result.list_revision);
      setConsumerContext({ listId, revision, requestId: result.request_id });
      const query = new URLSearchParams(window.location.search);
      query.set("list_id", listId);
      query.set("revision", String(revision));
      query.set("request_id", result.request_id);
      window.history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);
    } catch (cause) {
      setConsumerError(cause instanceof Error ? cause.message : "Could not optimize this list revision.");
    } finally {
      setConsumerLoading(false);
    }
  }

  if (!routeChecked) {
    return <AppShell><p role="status" className="text-sm text-muted-foreground">Loading optimization context…</p></AppShell>;
  }

  if (consumerContext) {
    const hasSynthetic = consumerResult?.requested_items.some((item) => item.evidence_class === "synthetic_demo") ?? false;
    const hasLegacyFixture = consumerResult?.requested_items.some((item) => item.evidence_class === "demo_fixture") ?? false;
    return <AppShell><div className="space-y-6">
      <PageHeader
        eyebrow="Shopping list optimization"
        title={`Comparison for list revision ${consumerResult?.list_revision ?? consumerContext.revision}`}
        description="Cartel compares the exact products and pack sizes saved in your shopping list. Observed product prices are not checkout totals; fees, taxes, discounts, serviceability, and payable amounts remain unknown without checkout information."
        action={<Link className="text-sm font-medium text-primary underline-offset-4 hover:underline" href={`/lists?list_id=${encodeURIComponent(consumerContext.listId)}`}>Back to list</Link>}
      />
      {consumerError && <p role="alert" className="text-sm text-destructive">{consumerError}</p>}
      {consumerLoading && <p role="status" className="text-sm text-muted-foreground">Loading the persisted optimization result…</p>}
      {!consumerResult && !consumerLoading && consumerContext.revision > 0 && (
        <Button data-testid="optimize-revision" onClick={() => void startOptimization(consumerContext.listId, consumerContext.revision)}>
          Optimize this revision
        </Button>
      )}
      {consumerResult && <section data-testid="consumer-optimization-result" className="space-y-5 border-y border-border py-5" aria-live="polite">
        {hasSynthetic && <p role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-800">
          This comparison uses the Cartel Demo synthetic catalog. Prices are synthetic and availability is simulated; this is not live retailer evidence. Delivery fees, taxes, discounts, serviceability, and checkout totals are unknown.
        </p>}
        {hasLegacyFixture && <p role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-800">
          Demo fixture evidence. This comparison uses deterministic fixture data only; it cannot produce a payable recommendation, savings claim, or checkout total.
        </p>}
        <OptimizationStatusGuide result={consumerResult} />
        <div>
          <h2 data-testid="consumer-optimization-status" className="font-semibold">{consumerResult.status === "ready" ? "A plan is ready to review" : consumerResult.status === "unresolved" ? "Some items need review" : consumerResult.status === "infeasible" ? "Cartel could not build a complete plan" : consumerResult.status === "no_plan" ? "No plan is available yet" : "Comparison unavailable"}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{consumerResult.explanation}</p>
          <p className="mt-2 text-xs text-muted-foreground">This comparison describes list revision {consumerResult.list_revision}; changes to the list require a new comparison.</p>
        </div>
        {currentListRevision === null ? <p role="status" className="text-xs text-muted-foreground">Current list revision could not be checked; this result is only guaranteed to describe revision {consumerResult.list_revision}.</p> : currentListRevision !== consumerResult.list_revision ? <p role="status" className="text-sm text-amber-700">Historical result for revision {consumerResult.list_revision}. The list is now revision {currentListRevision}; optimize the current revision for an updated result.</p> : null}
        <div>
          <h3 className="text-sm font-medium">What you asked for</h3>
          <ul className="mt-2 divide-y divide-border border-y border-border">{consumerResult.requested_items.map((item) => <li key={item.item_id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><span>{item.query} × {item.quantity}</span><span className="text-muted-foreground">{evidenceLabel(item.evidence_class) ? `${evidenceLabel(item.evidence_class)} · ` : ""}{item.resolution_status === "exact_confirmed" ? "Exact product confirmed" : "Product identity unresolved"}</span></li>)}</ul>
        </div>
        {consumerResult.unresolved_items.length > 0 && <p className="text-sm text-amber-700">{consumerResult.unresolved_items.length} item(s) are not covered by a payable recommendation. Missing fees, taxes, serviceability, or checkout evidence is reported rather than estimated.</p>}
        {consumerResult.status === "ready" && <div><h3 className="text-sm font-medium">Selected retailer groups</h3><p className="mt-1 text-xs text-muted-foreground">Retailers used: {new Set(selectedAllocations(consumerResult).map((allocation) => allocation.retailer_id)).size}</p><ul className="mt-2 divide-y divide-border border-y border-border">{selectedAllocations(consumerResult).map((allocation) => <li key={`${allocation.item_id}:${allocation.listing_provenance.observation_id}`} className="py-3 text-sm"><p>{consumerResult.requested_items.find((item) => item.item_id === allocation.item_id)?.query} × {allocation.quantity} · {allocation.retailer_id} ({allocation.listing_provenance.platform})</p><p className="text-xs text-muted-foreground">Observed unit price {money(allocation.listing_provenance.observed_selling_price.currency, allocation.listing_provenance.observed_selling_price.minor_units)}</p></li>)}</ul></div>}
        <div>
          <h3 className="text-sm font-medium">Observed product prices</h3>
          {consumerResult.offers.length === 0 ? <p className="mt-2 text-sm text-muted-foreground">No current offers are available for this list revision.</p> : <ul className="mt-2 divide-y divide-border border-y border-border">{consumerResult.offers.map((offer) => <li key={`${offer.item_id}:${offer.platform}:${offer.platform_listing_id}:${offer.observation_id}`} className="space-y-1 py-3 text-sm">
            <p>{consumerResult.requested_items.find((item) => item.item_id === offer.item_id)?.query} · {offer.platform} · quantity {offer.quantity}</p>
            <p>{offer.is_synthetic ? "Synthetic observed unit price " : "Observed unit price "}{money(offer.observed_unit_price.currency, offer.observed_unit_price.minor_units)} · {offer.is_synthetic ? "synthetic observed product subtotal " : "observed product subtotal "}{money(offer.observed_product_subtotal.currency, offer.observed_product_subtotal.minor_units)}</p>
            <p className="text-xs text-muted-foreground">{offer.is_synthetic ? "Simulated availability: " : "Availability: "}{offer.availability ?? "unknown"} · Fees and taxes: unknown</p>
            <p className="text-xs text-muted-foreground">Captured {new Date(offer.observed_at).toLocaleString()} · {offer.is_synthetic ? "Synthetic demo observation" : "Governed observation"}</p>
          </li>)}</ul>}
        </div>
        <p className="text-xs text-muted-foreground">Observed product subtotal excludes delivery, handling, platform fees, discounts, taxes, and checkout changes. No savings or payable total is asserted.</p>
        {consumerResult.optimizer_result && <p className="text-xs text-muted-foreground">This is a saved comparison, not user approval, checkout readiness, or an order instruction.</p>}
      </section>}
    </div></AppShell>;
  }

  const activeLists = lists.filter((list) => !list.archived);
  const selectedList = activeLists.find((list) => list.id === selectedListId);

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader eyebrow="Shopping list optimization" title="Compare a saved shopping list." description="Cartel compares the exact products and pack sizes saved in one of your shopping lists. Synthetic demo prices are not live retailer evidence or checkout totals." />

        <section aria-labelledby="list-context-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShoppingCart className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="list-context-heading" className="font-semibold">Choose a saved shopping list</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Optimization runs over a persisted list revision. Changes to the list require a new comparison.
              </p>
            </div>
          </div>

          {listsLoading ? (
            <p role="status" className="mt-8 text-sm text-muted-foreground">Loading your shopping lists…</p>
          ) : listsError ? (
            <div role="alert" className="mt-8 flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
              <span>{listsError}</span>
            </div>
          ) : activeLists.length === 0 ? (
            <div className="mt-8 rounded-xl border border-dashed border-border px-5 py-10 text-center">
              <p className="text-sm font-medium">No shopping list is ready</p>
              <p className="mt-2 text-sm text-muted-foreground">Create a list and add exact products before optimizing.</p>
              <Link href="/lists" className="mt-5 inline-flex h-10 items-center justify-center rounded-md border border-border px-4 text-sm font-medium hover:bg-muted">Manage lists</Link>
            </div>
          ) : (
            <div className="mt-8 space-y-4">
              <label className="grid gap-1.5 text-sm">
                <span className="font-medium">Shopping list</span>
                <select
                  value={selectedListId}
                  onChange={(event) => setSelectedListId(event.target.value)}
                  className="h-10 min-w-56 rounded-md border border-border bg-background px-3 text-sm"
                >
                  {activeLists.map((list) => <option key={list.id} value={list.id}>{list.name}</option>)}
                </select>
              </label>
              <p className="text-sm text-muted-foreground">
                {selectedList ? `${selectedList.items.length} saved item${selectedList.items.length === 1 ? "" : "s"} · revision ${selectedList.revision}.` : "Select a list to continue."}
              </p>
              {selectedList && selectedList.items.length === 0 && <p className="text-sm text-amber-700">This list has no items. Add products before optimizing.</p>}
              {consumerError && <p role="alert" className="text-sm text-destructive">{consumerError}</p>}
              {consumerLoading && (
                <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/30 p-4 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Persisting the optimization result…
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  data-testid="optimize-selected-list"
                  onClick={() => selectedList && void startOptimization(selectedList.id, selectedList.revision)}
                  disabled={!selectedList || selectedList.items.length === 0 || consumerLoading}
                >
                  {consumerLoading ? "Optimizing..." : "Optimize this list"}
                </Button>
              </div>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
