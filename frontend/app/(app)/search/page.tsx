"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Loader2, Search as SearchIcon, X } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { productSearchService, type ProductSearchResult } from "@/services/productSearch";
import { shoppingListsService } from "@/services/shoppingLists";
import type { ShoppingList } from "@/types/shoppingLists";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";

function selectionKey(product: ProductSearchResult["products"][number]): string {
  return [product.productId, product.variantId, product.platform, product.listingId, product.observationId].join("\u001f");
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [searchResult, setSearchResult] = useState<ProductSearchResult | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [lists, setLists] = useState<readonly ShoppingList[]>([]);
  const [selectedListId, setSelectedListId] = useState("");
  const [listsLoading, setListsLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [savingProductId, setSavingProductId] = useState<string | null>(null);
  const [selectedProducts, setSelectedProducts] = useState<Record<string, boolean>>({});
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const activeLists = useMemo(() => lists.filter((list) => !list.archived), [lists]);

  useEffect(() => {
    let mounted = true;
    void shoppingListsService.list().then((result) => {
      if (!mounted) return;
      setLists(result);
      setSelectedListId(result.find((list) => !list.archived)?.id ?? "");
    }).catch((error: unknown) => {
      if (mounted) setListError(error instanceof Error ? error.message : "Shopping lists are unavailable.");
    }).finally(() => { if (mounted) setListsLoading(false); });
    return () => { mounted = false; };
  }, []);

  const hasQuery = query.trim().length > 0;

  const submitSearch = async () => {
    if (!hasQuery || isSearching) return;
    setSearchError(null);
    setSearchResult(null);
    setSelectedProducts({});
    setQuantities({});
    setIsSearching(true);
    try {
      setSearchResult(await productSearchService.search(query));
      setSelectedProducts({});
      setQuantities({});
    } catch (error) {
      setSearchResult(null);
      setSearchError(error instanceof Error ? error.message : "Product search failed.");
    } finally {
      setIsSearching(false);
    }
  };

  const addToList = async (product: ProductSearchResult["products"][number]) => {
    if (!selectedListId || !product.variantId || !product.listingId || !product.observationId || savingProductId) return;
    const key = selectionKey(product);
    if (!selectedProducts[key]) {
      setListError("Select the exact product and pack before adding it to your list.");
      return;
    }
    setSavingProductId(key); setListError(null);
    try {
      const updated = await shoppingListsService.addItem(selectedListId, {
        query: searchResult?.query ?? query.trim(),
        quantity: quantities[key] ?? 1,
        canonical_product_id: product.productId,
        canonical_variant_id: product.variantId,
        source_platform: product.platform,
        source_listing_id: product.listingId,
        source_observation_id: product.observationId,
      });
      setLists((current) => current.map((list) => list.id === updated.id ? updated : list));
    } catch (error) {
      setListError(error instanceof Error ? error.message : "Could not save this product to your list.");
    } finally { setSavingProductId(null); }
  };

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader eyebrow="Product search" title="Find the exact product." description="Search Cartel's verified catalog, confirm the variant and pack, then save that exact choice to a persistent list." />

        <div className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5"><label htmlFor="shopping-list-target" className="text-sm font-medium">Save to list</label>
            <select id="shopping-list-target" value={selectedListId} onChange={(event) => setSelectedListId(event.target.value)} disabled={listsLoading || activeLists.length === 0} className="h-10 min-w-56 rounded-md border border-border bg-background px-3 text-sm">
              {activeLists.length === 0 ? <option value="">No active lists</option> : activeLists.map((list) => <option key={list.id} value={list.id}>{list.name}</option>)}
            </select>
          </div>
          <Link href="/lists" className="inline-flex h-10 items-center justify-center rounded-md border border-border px-4 text-sm font-medium hover:bg-muted">Manage lists</Link>
        </div>
        {listError && <p role="alert" className="text-sm text-destructive">{listError}</p>}
        {!listsLoading && activeLists.length === 0 && <p className="text-sm text-muted-foreground">Create a shopping list before saving products.</p>}

        <form
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            void submitSearch();
          }}
          className="flex items-center gap-3 rounded-2xl border border-border bg-card p-2 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/20"
        >
          <SearchIcon className="ml-3 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search groceries..."
            aria-label="Search groceries"
            className="min-w-0 flex-1 bg-transparent px-1 py-2 text-sm outline-none placeholder:text-muted-foreground"
          />
          {query && (
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label="Clear search"
              onClick={() => {
                setQuery("");
                setSearchResult(null);
                setSearchError(null);
              }}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
          <Button type="submit" disabled={!hasQuery || isSearching}>
            {isSearching ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : "Search"}
          </Button>
        </form>

        <section aria-live="polite" aria-labelledby="results-heading" className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 id="results-heading" className="text-lg font-semibold tracking-tight">
                {hasQuery ? "Search results" : "Products"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {hasQuery
                  ? "Results from Cartel's verified product catalog."
                  : "Search to begin building your cart."}
              </p>
            </div>
          </div>

          {isSearching ? (
            <div className="rounded-2xl border border-border bg-card px-6 py-16 text-center" aria-label="Searching">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" aria-hidden="true" />
              <h3 className="mt-4 font-semibold">Checking verified products</h3>
              <p className="mt-2 text-sm text-muted-foreground">Checking the supported catalog for an exact match.</p>
            </div>
          ) : searchError ? (
            <StatePanel icon={SearchIcon} title="Product search unavailable" description={searchError} tone="danger" />
          ) : searchResult?.products.length === 0 || !searchResult ? (
            <StatePanel icon={SearchIcon} title={hasQuery ? "No verified match yet" : "Search the verified catalog"} description={hasQuery ? "Cartel found no exact product with retailer information it can safely connect to this request. No similar product was substituted." : "Enter a grocery item above to inspect exact products and pack sizes."} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {searchResult?.products.map((product) => (
                <article key={selectionKey(product)} className={`surface-lift rounded-2xl border bg-card p-5 ${selectedProducts[selectionKey(product)] ? "border-primary ring-2 ring-primary/15" : "border-border"}`}>
                  <p className="text-xs text-muted-foreground">{product.platform}</p>
                  <h3 className="mt-3 font-semibold">{product.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Brand: {product.brand ?? "Not specified"}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{product.pack ?? "Pack information unavailable"}</p>
                  <p className="mt-2 text-xs text-muted-foreground">Exact product selected · {product.platform}</p>
                  {product.identityAttributes?.length ? <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">{product.identityAttributes.map((attribute) => <li key={`product:${attribute.name}:${attribute.value}`}>{attribute.name}: {attribute.value}{attribute.assertionStatus !== "asserted" ? ` (${attribute.assertionStatus})` : ""}</li>)}</ul> : null}
                  {product.variantAttributes?.length ? <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">{product.variantAttributes.map((attribute) => <li key={`${attribute.name}:${attribute.value}`}>{attribute.name}: {attribute.value}{attribute.assertionStatus !== "asserted" ? ` (${attribute.assertionStatus})` : ""}</li>)}</ul> : null}
                  <label className="mt-4 flex cursor-pointer items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(selectedProducts[selectionKey(product)])}
                      disabled={!product.variantId || !product.listingId || !product.observationId || product.evidenceState !== "registered_governed_observation"}
                      onChange={(event) => setSelectedProducts((current) => ({ ...current, [selectionKey(product)]: event.target.checked }))}
                      className="mt-0.5"
                    />
                    <span>Select this exact variant</span>
                  </label>
                  <div className="mt-4 flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium">
                      {product.price ? `${product.price.currency} ${(product.price.minorUnits / 100).toFixed(2)}` : "Price unavailable"}
                    </span>
                    <span className={product.availability ? "text-emerald-600" : "text-muted-foreground"}>
                      {product.availability ?? "Availability unavailable"}
                    </span>
                  </div>
                  <label className="mt-4 grid gap-1.5 text-sm">
                    <span>Quantity</span>
                    <input type="number" min={1} max={999} value={quantities[selectionKey(product)] ?? 1} onChange={(event) => setQuantities((current) => ({ ...current, [selectionKey(product)]: Math.max(1, Math.min(999, Number(event.target.value) || 1)) }))} disabled={!product.variantId || !selectedProducts[selectionKey(product)]} className="h-10 w-24 rounded-md border border-border bg-background px-3" />
                  </label>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{product.evidenceState === "registered_governed_observation" ? "Verified catalog observation" : "Evidence unavailable"}{product.observedAt ? ` · captured ${new Date(product.observedAt).toLocaleString()}` : ""}. Price and availability are observed facts, not a checkout quote.</p>
                  <Button className="mt-5 w-full" onClick={() => void addToList(product)} disabled={!selectedListId || !product.variantId || !product.listingId || !product.observationId || product.evidenceState !== "registered_governed_observation" || !selectedProducts[selectionKey(product)] || savingProductId !== null}>
                    {savingProductId === selectionKey(product) ? "Saving…" : "Add selected variant to list"}
                  </Button>
                  {savingProductId !== selectionKey(product) && lists.find((list) => list.id === selectedListId)?.items.some((item) => item.canonical_variant_id === product.variantId && item.source_observation_id === product.observationId) && <p role="status" className="mt-2 text-sm text-emerald-700">Saved to {lists.find((list) => list.id === selectedListId)?.name}.</p>}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
