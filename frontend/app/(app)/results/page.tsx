"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, CheckCircle2, CircleHelp, ExternalLink } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { useCartStore } from "@/store/cartStore";
import type { ItemAllocation } from "@/types/cartOptimization";

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
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Optimization result</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">A clearer way to buy this cart.</h1>
          <p className="max-w-2xl text-muted-foreground">
            Review the governed result and its evidence. Costs are shown only when the optimization response contains an effective-cost value.
          </p>
        </header>

        {automaticPlanning?.status === "unresolved" && !optimizationResult && (
          <section role="alert" className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6">
            <h2 className="font-semibold">Cartel could not safely build a plan</h2>
            <p className="mt-2 text-sm text-muted-foreground">No estimates were substituted for missing governed data.</p>
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {automaticPlanning.unresolved_reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            <Link href="/cart" className="mt-5 inline-flex text-sm font-medium text-primary hover:underline">Review cart</Link>
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
                <p className="mt-2 text-sm text-muted-foreground">
                  Request {optimizationResult.request_id} / Optimization {optimizationResult.optimization_id}
                </p>
              </div>
              <div className={`rounded-full px-3 py-1 text-sm font-medium ${optimizationResult.outcome === "selected" ? "bg-green-500/10 text-green-700" : "bg-amber-500/10 text-amber-700"}`}>
                {optimizationResult.outcome}
              </div>
            </div>

            {plan ? (
              <>
                <div className="grid gap-4 sm:grid-cols-3">
                  <article className="rounded-2xl border border-border bg-card p-5">
                    <p className="text-sm text-muted-foreground">Effective cost</p>
                    <p className="mt-2 text-lg font-semibold">Checkout evidence linked</p>
                    <p className="mt-1 text-xs text-muted-foreground">The optimizer uses checkout-derived evidence, not listing price alone. Amount details are unavailable in this result contract.</p>
                  </article>
                  <article className="rounded-2xl border border-border bg-card p-5">
                    <p className="text-sm text-muted-foreground">Checkouts</p>
                    <p className="mt-2 text-lg font-semibold">{plan.checkout_groups.length}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Declared checkout groups in the selected plan.</p>
                  </article>
                  <article className="rounded-2xl border border-border bg-card p-5">
                    <p className="text-sm text-muted-foreground">Feasibility</p>
                    <p className="mt-2 text-lg font-semibold">{plan.feasibility}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Plan {plan.plan_id} · ECE {plan.effective_cost_evaluation_reference.effective_cost_evaluation_id}</p>
                  </article>
                </div>

                <section aria-labelledby="selected-plan-heading" className="rounded-2xl border border-border bg-card p-6 sm:p-8">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 id="selected-plan-heading" className="text-lg font-semibold">Selected allocation</h3>
                      <p className="mt-1 text-sm text-muted-foreground">{optimizationResult.rationale.join(" ") || "No rationale was provided."}</p>
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      <p>Inconvenience units: {plan.inconvenience_penalty_units}</p>
                      <p>Preference priority: {plan.retailer_preference_priority}</p>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4 lg:grid-cols-2">
                    {Object.entries(allocationsByRetailer).map(([retailerId, allocations]) => (
                      <article key={retailerId} className="rounded-xl border border-border p-4">
                        <div className="flex items-center justify-between gap-3">
                          <h4 className="font-semibold">Retailer {retailerId}</h4>
                          <span className="text-xs text-muted-foreground">{allocations.length} allocation{allocations.length === 1 ? "" : "s"}</span>
                        </div>
                        <div className="mt-3 divide-y divide-border">
                          {allocations.map((allocation) => (
                            <div key={`${allocation.item_id}:${allocation.checkout_group_id}`} className="flex justify-between gap-4 py-3 text-sm">
                              <div>
                                <p className="font-medium">{allocation.item_id}</p>
                                <p className="text-xs text-muted-foreground">Variant {allocation.canonical_variant_id}</p>
                              </div>
                              <div className="text-right">
                                <p>Quantity {allocation.quantity}</p>
                                <p className="text-xs text-muted-foreground">Group {allocation.checkout_group_id}</p>
                                {plan.candidate_item_allocations?.find((candidate) => candidate.item_id === allocation.item_id)?.listing_provenance?.observed_selling_price && (
                                  <p className="text-xs text-muted-foreground">
                                    Listed {plan.candidate_item_allocations.find((candidate) => candidate.item_id === allocation.item_id)?.listing_provenance?.observed_selling_price?.currency} {(plan.candidate_item_allocations.find((candidate) => candidate.item_id === allocation.item_id)?.listing_provenance?.observed_selling_price?.minor_units ?? 0) / 100}
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
                      <p className="mt-2 flex items-start gap-2 text-sm text-muted-foreground"><ExternalLink className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> No supported listing URL or execution handoff is present in the result contract.</p>
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
                      <p className="font-medium">Plan {alternative.plan_id}</p>
                      <p className="mt-1 text-muted-foreground">Feasibility: {alternative.feasibility}</p>
                      <p className="text-muted-foreground">Checkouts: {alternative.checkout_groups.length}</p>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </section>
        )}

        {!resolution && !automaticPlanning ? (
          <section className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-20 text-center">
            <CircleHelp className="mx-auto h-9 w-9 text-muted-foreground/60" aria-hidden="true" />
            <h2 className="mt-5 text-lg font-semibold">No resolution result yet</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">Resolve a populated cart first.</p>
            <Link href="/optimize" className="mt-6 inline-flex text-sm font-medium text-primary hover:underline">Prepare cart</Link>
          </section>
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
                          <p>Product: {item.canonical_product_id}</p>
                          <p>Variant: {item.canonical_variant_id}</p>
                          {item.platform && <p>Listing: {item.platform} / {item.platform_listing_id}</p>}
                          {item.observation_id && <p>Observation: {item.observation_id}</p>}
                          {candidateItem && (
                            <div className="mt-3 space-y-2">
                              <p>
                                Persisted candidates: {candidateItem.candidates.length} ({candidateItem.status.replaceAll("_", " ")})
                              </p>
                              {candidateItem.reason && (
                                <p className="text-amber-600">{candidateItem.reason}</p>
                              )}
                              {candidateItem.candidates.length > 0 && (
                                <div className="space-y-2 border-l border-border pl-3">
                                  {candidateItem.candidates.map((candidate, candidateIndex) => (
                                    <div key={`${candidate.platform}:${candidate.platform_listing_id}:${candidate.observation_id}:${candidateIndex}`}>
                                      <p className="font-medium text-foreground">
                                        {candidate.platform} / {candidate.platform_listing_id}
                                      </p>
                                      <p>
                                        Observation: {candidate.observation_id} · {candidate.readiness.replaceAll("_", " ")}
                                      </p>
                                      {candidate.readiness_reason && (
                                        <p className="text-amber-600">{candidate.readiness_reason}</p>
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
                      {resolved ? "Resolved" : "Unresolved"}
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
