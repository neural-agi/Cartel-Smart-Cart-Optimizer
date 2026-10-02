"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Loader2, Search as SearchIcon, X } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { productSearchService, type ProductSearchResult } from "@/services/productSearch";
import { shoppingListsService } from "@/services/shoppingLists";
import type { ShoppingList } from "@/types/shoppingLists";
import { useCartStore } from "@/store/cartStore";

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
  const addItem = useCartStore((state) => state.addItem);
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
    setIsSearching(true);
    try {
      setSearchResult(await productSearchService.search(query));
    } catch (error) {
      setSearchResult(null);
      setSearchError(error instanceof Error ? error.message : "Product search failed.");
    } finally {
      setIsSearching(false);
    }
  };

  const addToList = async (product: ProductSearchResult["products"][number]) => {
    if (!selectedListId || !product.variantId || !product.listingId || !product.observationId || savingProductId) return;
    const key = product.variantId;
    setSavingProductId(key); setListError(null);
    try {
      const updated = await shoppingListsService.addItem(selectedListId, {
        query: searchResult?.query ?? query.trim(),
        quantity: 1,
        canonical_product_id: product.productId,
        canonical_variant_id: product.variantId,
        source_platform: product.platform,
        source_listing_id: product.listingId,
        source_observation_id: product.observationId,
      });
      setLists((current) => current.map((list) => list.id === updated.id ? updated : list));
      addItem(product);
    } catch (error) {
      setListError(error instanceof Error ? error.message : "Could not save this product to your list.");
    } finally { setSavingProductId(null); }
  };

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Product search</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Find what you need.</h1>
          <p className="max-w-2xl text-muted-foreground">Search the governed catalog, then save the selected variant and its source observation to one of your persistent lists.</p>
        </header>

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
                  ? "Results from the governed canonical catalog."
                  : "Search to begin building your cart."}
              </p>
            </div>
          </div>

          {isSearching ? (
            <div className="rounded-2xl border border-border bg-card px-6 py-16 text-center" aria-label="Searching">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" aria-hidden="true" />
              <h3 className="mt-4 font-semibold">Searching governed products</h3>
              <p className="mt-2 text-sm text-muted-foreground">Checking the supported catalog for an exact match.</p>
            </div>
          ) : searchError ? (
            <div role="alert" className="rounded-2xl border border-destructive/40 bg-destructive/5 px-6 py-10 text-center">
              <h3 className="font-semibold">Product search unavailable</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{searchError}</p>
            </div>
          ) : searchResult?.products.length === 0 || !searchResult ? (
            <div className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-16 text-center">
              <SearchIcon className="mx-auto h-8 w-8 text-muted-foreground/60" aria-hidden="true" />
              <h3 className="mt-4 font-semibold">No products to show yet</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                {hasQuery
                  ? "No governed product/listing observations matched this query."
                  : "Enter a grocery item above to search the catalog."}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {searchResult?.products.map((product) => (
                <article key={product.variantId ?? product.listingId ?? product.productId} className="rounded-2xl border border-border bg-card p-5">
                  <p className="text-xs text-muted-foreground">{product.platform}</p>
                  <h3 className="mt-3 font-semibold">{product.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{product.pack ?? "Pack information unavailable"}</p>
                  <div className="mt-4 flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium">
                      {product.price ? `${product.price.currency} ${(product.price.minorUnits / 100).toFixed(2)}` : "Price unavailable"}
                    </span>
                    <span className={product.availability ? "text-emerald-600" : "text-muted-foreground"}>
                      {product.availability ?? "Availability unavailable"}
                    </span>
                  </div>
                  <Button className="mt-5 w-full" onClick={() => void addToList(product)} disabled={!selectedListId || !product.variantId || !product.listingId || !product.observationId || savingProductId !== null || product.availability === "unavailable"}>
                    {savingProductId === product.variantId ? "Saving…" : "Add to list"}
                  </Button>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
