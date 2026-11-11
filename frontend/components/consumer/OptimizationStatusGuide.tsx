import { AlertCircle, CheckCircle2, CircleHelp } from "lucide-react";

import type { ConsumerOptimizationResult } from "@/types/consumerOptimization";

const statuses = [
  {
    key: "ready",
    title: "Ready",
    meaning:
      "Every requested item has exact product evidence, so Cartel can describe a complete comparison.",
  },
  {
    key: "partial",
    title: "Partial",
    meaning:
      "Some items are covered and at least one is unresolved or lacks checkout evidence. A partial result is not a failed calculation: it reports exactly what is known and what is still missing.",
  },
  {
    key: "unresolved",
    title: "Unresolved",
    meaning:
      "Cartel could not match enough items to supported exact products, so it does not assert a comparison.",
  },
] as const;

function currentStatus(result: ConsumerOptimizationResult): "ready" | "partial" | "unresolved" {
  if (result.status === "ready") return "ready";
  if (result.status === "unresolved") return "unresolved";
  return "partial";
}

const statusIcons = {
  ready: CheckCircle2,
  partial: CircleHelp,
  unresolved: AlertCircle,
} as const;

interface OptimizationStatusGuideProps {
  result: ConsumerOptimizationResult;
}

export default function OptimizationStatusGuide({ result }: OptimizationStatusGuideProps) {
  const active = currentStatus(result);

  return (
    <section
      data-testid="optimization-status-guide"
      aria-labelledby="optimization-status-guide-heading"
      className="rounded-2xl border border-border bg-muted/20 p-5"
    >
      <h3 id="optimization-status-guide-heading" className="font-semibold">
        How to read this comparison
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Current result: <span data-testid="optimization-status-current">{active}</span>
      </p>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        {statuses.map((status) => {
          const Icon = statusIcons[status.key];
          const isActive = status.key === active;
          return (
            <div
              key={status.key}
              data-testid={`status-guide-${status.key}`}
              data-active={isActive ? "true" : "false"}
              className={`rounded-xl border p-4 ${
                isActive ? "border-primary/40 bg-primary/5" : "border-border bg-card"
              }`}
            >
              <dt className="flex items-center gap-2 text-sm font-medium">
                <Icon className="h-4 w-4" aria-hidden="true" />
                {status.title}
              </dt>
              <dd className="mt-2 text-xs leading-5 text-muted-foreground">{status.meaning}</dd>
            </div>
          );
        })}
      </dl>

      <ul className="mt-4 space-y-1 text-xs leading-5 text-muted-foreground">
        <li data-testid="status-guide-synthetic">
          Synthetic demo listings are simulated. They are not live retailer evidence.
        </li>
        <li data-testid="status-guide-checkout">Real checkout totals are unavailable.</li>
        <li data-testid="status-guide-unknowns">
          Fees, taxes, discounts, and serviceability are unknown.
        </li>
        <li data-testid="status-guide-not-failure">
          A partial result is not a failed calculation.
        </li>
        <li data-testid="status-guide-no-claims">
          Cartel does not show a payable total, savings figure, or best-price claim from synthetic
          listings.
        </li>
      </ul>
    </section>
  );
}
