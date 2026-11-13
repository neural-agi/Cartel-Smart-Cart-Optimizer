"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle2, CircleHelp, ExternalLink } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { useCartStore } from "@/store/cartStore";
import type { ItemAllocation } from "@/types/cartOptimization";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";
import { consumerReason } from "@/lib/consumerCopy";

export default function ResultsPage() {
  const items = useCartStore((state) => state.items);
  const resolution = useCartStore((state) => state.resolution);
  const candidateDiscovery = useCartStore((state) => state.candidateDiscovery);
  const optimizationResult = useCartStore((state) => state.optimizationResult);
  const automaticPlanning = useCartStore((state) => state.automaticPlanning);

  const plan = optimizationResult?.chosen_plan;
  const allocationsByRetailer: Record<string, ItemAllocation[]> = plan
    ? plan.item_allocations.reduce<Record<string, ItemAllocation[]>>((groups, allocation) => {
        (groups[allocation.retailer_id] ??= []).push(allocation);
        return groups;
      }, {})
    : {};

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader eyebrow="Optimization result" title="A clearer way to buy this cart." description="Review what Cartel could determine from current supported evidence. Observed prices are not guaranteed checkout totals." />

        {automaticPlanning?.status === "unresolved" && !optimizationResult && (
          <section role="alert" className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6">
            <h2 className="font-semibold">Cartel could not safely build a plan</h2>
            <p className="mt-2 text-sm text-muted-foreground">Cartel could not safely determine where this cart should be bought. No estimates were substituted for missing information.</p>
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {consumerReason(automaticPlanning.unresolved_reasons[0] ?? "").length > 0 && <li>{consumerReason(automaticPlanning.unresolved_reasons[0] ?? "")}</li>}
            </ul>
            <Link href="/cart" className="mt-5 inline-flex text-sm font-medium text-primary hover:underline">Review cart</Link>
          </section>
        )}

        {automaticPlanning?.status === "unavailable" && !optimizationResult && (
          <section role="alert" className="rounded-2xl border border-orange-500/30 bg-orange-500/5 p-6">
            <h2 className="font-semibold">Checkout information is unavailable</h2>
            <p className="mt-2 text-sm text-muted-foreground">Cartel could not verify a checkout total, so this result does not estimate what you would pay.</p>
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {consumerReason(automaticPlanning.unresolved_reasons[0] ?? "").length > 0 && <li>{consumerReason(automaticPlanning.unresolved_reasons[0] ?? "")}</li>}
            </ul>
          </section>
        )}

        {optimizationResult && (
          <section aria-labelledby="optimization-result-heading" className="space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-border bg-card p-6 sm:p-8">
              <div>
                <p className="text-sm font-medium text-primary">Optimization result</p>
                <h2 id="optimization-result-heading" className="mt-1 text-2xl font-bold">
                  {optimizationResult.outcome === "selected"
                    ? "Recommended plan"
                    : optimizationResult.outcome === "infeasible"
                      ? "No feasible plan"
                      : "Optimization unresolved"}
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">This is a saved comparison for the items and evidence available when you started optimization.</p>
              </div>
              <div className={`rounded-full px-3 py-1 text-sm font-medium ${optimizationResult.outcome === "selected" ? "bg-green-500/10 text-green-700" : "bg-amber-500/10 text-amber-700"}`}>
                {optimizationResult.outcome === "selected" ? "Plan found" : optimizationResult.outcome === "infeasible" ? "Not possible yet" : "Needs review"}
              </div>
            </div>

            {plan ? (
              <>
                <div className="grid gap-4 sm:grid-cols-3">
                  <article className="surface-lift rounded-2xl border border-border bg-card p-5">
                    <p className="text-sm text-muted-foreground">Checkout total</p>
                    <p className="mt-2 text-lg font-semibold">Not available</p>
                    <p className="mt-1 text-xs text-muted-foreground">Observed product prices do not include delivery, fees, discounts, or checkout changes.</p>
                  </article>
                  <article className="surface-lift rounded-2xl border border-border bg-card p-5">
                    <p className="text-sm text-muted-foreground">Retailer groups</p>
                    <p className="mt-2 text-lg font-semibold">{plan.checkout_groups.length}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Separate retailer groupings in this comparison.</p>
                  </article>
                  <article className="surface-lift rounded-2xl border border-border bg-card p-5">
                    <p className="text-sm text-muted-foreground">Plan status</p>
                    <p className="mt-2 text-lg font-semibold">{plan.feasibility === "feasible" ? "Ready to review" : "Needs review"}</p>
                    <p className="mt-1 text-xs text-muted-foreground">This is a comparison, not an order or payment authorization.</p>
                  </article>
                </div>

                <section aria-labelledby="selected-plan-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 id="selected-plan-heading" className="text-lg font-semibold">Selected allocation</h3>
                      <p className="mt-1 text-sm text-muted-foreground">{optimizationResult.rationale.join(" ") || "Cartel selected this grouping from the available product evidence."}</p>
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      <p>{plan.checkout_groups.length} retailer group{plan.checkout_groups.length === 1 ? "" : "s"}</p>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4 lg:grid-cols-2">
                    {Object.entries(allocationsByRetailer).map(([retailerId, allocations]) => (
                      <article key={retailerId} className="rounded-xl border border-border p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h4 className="font-semibold">{retailerId}</h4>
                          <span className="text-xs text-muted-foreground">{allocations.length} allocation{allocations.length === 1 ? "" : "s"}</span>
                        </div>
                        <div className="mt-3 divide-y divide-border">
                          {allocations.map((allocation) => (
                            <div key={`${allocation.item_id}:${allocation.checkout_group_id}`} className="flex justify-between gap-4 py-3 text-sm">
                              <div>
                                <p className="font-medium">{allocation.item_id}</p>
                                <p className="text-xs text-muted-foreground">Exact product selected</p>
                              </div>
                              <div className="text-right">
                                <p>Quantity {allocation.quantity}</p>
                                {plan.candidate_item_allocations?.find((candidate) => candidate.item_id === allocation.item_id)?.listing_provenance?.observed_selling_price && (
                                  <p className="text-xs text-muted-foreground">
                                    Observed price {plan.candidate_item_allocations.find((candidate) => candidate.item_id === allocation.item_id)?.listing_provenance?.observed_selling_price?.currency} {(plan.candidate_item_allocations.find((candidate) => candidate.item_id === allocation.item_id)?.listing_provenance?.observed_selling_price?.minor_units ?? 0) / 100}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>

                  <div className="mt-6 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-xl bg-muted/40 p-4">
                      <h4 className="font-semibold">Cost comparison</h4>
                      <p className="mt-2 text-sm text-muted-foreground">Savings and comparable baseline are unavailable because no effective-cost amounts are included in this result.</p>
                    </div>
                    <div className="rounded-xl bg-muted/40 p-4">
                      <h4 className="font-semibold">Retailer handoff</h4>
                      <p className="mt-2 flex items-start gap-2 text-sm text-muted-foreground"><ExternalLink className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> Cartel could not provide a supported retailer handoff for this result.</p>
                    </div>
                  </div>
                </section>

                {(optimizationResult.unknowns.length > 0 || optimizationResult.assumptions.length > 0) && (
                  <section className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6">
                    <h3 className="font-semibold">Important limitations</h3>
                    <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                      {[...optimizationResult.unknowns, ...optimizationResult.assumptions].map((entry) => <li key={entry}>{entry}</li>)}
                    </ul>
                  </section>
                )}
              </>
            ) : (
              <section role="alert" className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6">
                <h3 className="font-semibold">No recommendation is available</h3>
                <p className="mt-2 text-sm text-muted-foreground">{optimizationResult.rationale.join(" ") || "The optimizer did not select a plan."}</p>
              </section>
            )}

            {optimizationResult.alternative_plans.length > 0 && (
              <section aria-labelledby="alternatives-heading" className="rounded-2xl border border-border bg-card p-6">
                <h3 id="alternatives-heading" className="font-semibold">Alternatives</h3>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {optimizationResult.alternative_plans.map((alternative) => (
                    <article key={alternative.plan_id} className="rounded-xl border border-border p-4 text-sm">
                      <p className="font-medium">Alternative comparison</p>
                      <p className="mt-1 text-muted-foreground">{alternative.feasibility === "feasible" ? "Ready to review" : "Needs review"}</p>
                      <p className="text-muted-foreground">{alternative.checkout_groups.length} retailer group{alternative.checkout_groups.length === 1 ? "" : "s"}</p>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </section>
        )}

        {!resolution && !automaticPlanning ? (
            <StatePanel icon={CircleHelp} title="Nothing to compare yet" description="Add items to your cart, then start an optimization to see which supported purchase paths Cartel can verify." action={<Link href="/optimize" className="text-sm font-medium text-primary hover:underline">Prepare cart</Link>} />
        ) : resolution ? (
          <section aria-labelledby="resolved-items-heading" className="space-y-4">
            <h2 id="resolved-items-heading" className="text-lg font-semibold">Cart items</h2>
            <div className="divide-y divide-border rounded-2xl border border-border bg-card px-5">
              {resolution.items.map((item) => {
                const product = items.find((cartItem) => cartItem.itemId === item.item_id)?.product;
                const resolved = item.status === "resolved";
                const candidateItem = candidateDiscovery?.items.find(
                  (candidate) => candidate.item_id === item.item_id,
                );
                return (
                  <article key={item.item_id} className="flex items-start justify-between gap-4 py-5">
                    <div className="min-w-0">
                      <h3 className="font-medium">{product?.name ?? item.item_id}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">Quantity: {item.quantity}</p>
                      {resolved ? (
                        <div className="mt-3 space-y-1 text-xs text-muted-foreground">
                          {item.platform && <p>Retailer evidence available from {item.platform}.</p>}
                          {candidateItem && (
                            <div className="mt-3 space-y-2">
                              <p>{candidateItem.candidates.length} supported option{candidateItem.candidates.length === 1 ? "" : "s"} found.</p>
                              {candidateItem.reason && (
                                <p className="text-amber-600">{candidateItem.reason}</p>
                              )}
                              {candidateItem.candidates.length > 0 && (
                                <div className="space-y-2 border-l border-border pl-3">
                                  {candidateItem.candidates.map((candidate, candidateIndex) => (
                                    <div key={`${candidate.platform}:${candidate.platform_listing_id}:${candidate.observation_id}:${candidateIndex}`}>
                                      <p className="font-medium text-foreground">
                                        {candidate.platform} option
                                      </p>
                                      <p>
                                        {candidate.readiness === "ready_for_allocation" ? "Available for comparison" : "Needs more verified information"}
                                      </p>
                                      {candidate.readiness_reason && (
                        <p className="text-amber-600">{consumerReason(candidate.readiness_reason)}</p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="mt-3 text-sm text-destructive">{item.reason ?? "Item could not be resolved."}</p>
                      )}
                    </div>
                    <div className={`flex shrink-0 items-center gap-2 text-sm ${resolved ? "text-green-600" : "text-amber-600"}`}>
                      {resolved ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <AlertCircle className="h-4 w-4" aria-hidden="true" />}
                      {resolved ? "Ready" : "Needs review"}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ) : null}

        <Link href="/cart" className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to cart
        </Link>
      </div>
    </AppShell>
  );
}
