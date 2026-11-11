"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ListChecks, Search, ShoppingCart } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { buttonVariants } from "@/components/ui/button";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";
import { shoppingListsService } from "@/services/shoppingLists";
import type { ShoppingList, ShoppingListItem } from "@/types/shoppingLists";

function evidenceLabel(evidenceClass: ShoppingListItem["evidence_class"]): string | null {
  if (evidenceClass === "synthetic_demo") return "Synthetic demo";
  if (evidenceClass === "demo_fixture") return "Demo fixture";
  return null;
}

export default function CartPage() {
  const [lists, setLists] = useState<readonly ShoppingList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    void shoppingListsService
      .list()
      .then((result) => {
        if (mounted) setLists(result);
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setError(
            cause instanceof Error ? cause.message : "Your saved basket is unavailable right now.",
          );
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const basketLists = lists.filter((list) => !list.archived && list.items.length > 0);
  const itemCount = basketLists.reduce((total, list) => total + list.items.length, 0);
  const hasSynthetic = basketLists.some((list) =>
    list.items.some((item) => item.evidence_class === "synthetic_demo"),
  );

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader
          eyebrow="Saved basket"
          title="Your basket, from your saved lists."
          description="This basket is your persisted shopping-list data. Review each list, then compare the exact products and pack sizes you saved."
          action={
            <Link href="/lists" className={buttonVariants({ variant: "outline" })}>
              Manage lists
            </Link>
          }
        />

        <p data-testid="cart-data-source" className="text-xs text-muted-foreground">
          Data source: your persisted shopping lists (GET /api/v2/lists). This page does not keep a
          separate local cart.
        </p>

        {hasSynthetic && (
          <p
            data-testid="cart-synthetic-notice"
            role="status"
            className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-800"
          >
            Some items use the Cartel Demo synthetic catalog. Listings are simulated and are not
            live retailer evidence. Checkout totals, fees, taxes, discounts, and serviceability are
            unknown.
          </p>
        )}

        {loading ? (
          <p role="status" className="text-sm text-muted-foreground">
            Loading your saved basket…
          </p>
        ) : error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : basketLists.length === 0 ? (
          <StatePanel
            icon={ShoppingCart}
            title="Your basket is empty"
            description="Your saved shopping lists have no items yet. Search for an exact product to add to a list, or manage the lists you already have."
            action={
              <div className="flex flex-wrap justify-center gap-3">
                <Link href="/search" className={buttonVariants()}>
                  <Search className="h-4 w-4" aria-hidden="true" />
                  Search products
                </Link>
                <Link href="/lists" className={buttonVariants({ variant: "outline" })}>
                  <ListChecks className="h-4 w-4" aria-hidden="true" />
                  Manage lists
                </Link>
              </div>
            }
          />
        ) : (
          <section aria-labelledby="basket-heading" className="space-y-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="basket-heading" className="text-lg font-semibold">
                Saved list items
              </h2>
              <p data-testid="cart-item-count" className="text-sm text-muted-foreground">
                {itemCount} item{itemCount === 1 ? "" : "s"} across {basketLists.length} list
                {basketLists.length === 1 ? "" : "s"}
              </p>
            </div>

            <div className="space-y-4">
              {basketLists.map((list) => (
                <article
                  key={list.id}
                  data-testid="cart-list"
                  className="rounded-2xl border border-border bg-card p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate font-semibold">{list.name}</h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Revision {list.revision} · {list.items.length} item
                        {list.items.length === 1 ? "" : "s"}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        href={`/optimize?list_id=${encodeURIComponent(list.id)}&revision=${list.revision}`}
                        className={buttonVariants({ size: "sm" })}
                        data-testid="cart-optimize-list"
                      >
                        Optimize this list
                      </Link>
                      <Link
                        href={`/lists?list_id=${encodeURIComponent(list.id)}`}
                        className={buttonVariants({ variant: "outline", size: "sm" })}
                      >
                        Manage in lists
                      </Link>
                    </div>
                  </div>

                  <ul className="mt-4 divide-y divide-border border-y border-border">
                    {list.items.map((item) => {
                      const label = evidenceLabel(item.evidence_class);
                      return (
                        <li
                          key={item.id}
                          data-testid="cart-item"
                          className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
                        >
                          <div className="min-w-0">
                            <p className="truncate font-medium">{item.display_name ?? item.query}</p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              Quantity {item.quantity}
                              {item.unit ? ` · ${item.unit}` : ""} ·{" "}
                              {item.resolution_status === "exact_confirmed"
                                ? "Exact product saved"
                                : "Product match unresolved"}
                            </p>
                          </div>
                          {label && (
                            <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-800">
                              {label}
                            </span>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </article>
              ))}
            </div>

            <p className="text-xs leading-5 text-muted-foreground">
              This basket shows saved list items only. Observed product prices are not checkout
              totals; fees, taxes, discounts, serviceability, and payable amounts remain unknown
              without checkout evidence.
            </p>
          </section>
        )}
      </div>
    </AppShell>
  );
}
