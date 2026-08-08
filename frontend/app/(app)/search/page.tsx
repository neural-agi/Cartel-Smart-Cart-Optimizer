"use client";

import { useState } from "react";
import { Search as SearchIcon, X } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";

interface ProductResult {
  id: string;
  name: string;
  pack: string;
  retailer: string;
  priceMinorUnits?: number;
}

const productResults: ProductResult[] = [];

export default function SearchPage() {
  const [query, setQuery] = useState("");

  const hasQuery = query.trim().length > 0;

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Product search</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Find what you need.</h1>
          <p className="max-w-2xl text-muted-foreground">
            Search across your supported grocery platforms and build your cart one item at a time.
          </p>
        </header>

        <form
          role="search"
          onSubmit={(event) => event.preventDefault()}
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
              onClick={() => setQuery("")}
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
          <Button type="submit">Search</Button>
        </form>

        <section aria-live="polite" aria-labelledby="results-heading" className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 id="results-heading" className="text-lg font-semibold tracking-tight">
                {hasQuery ? "Search results" : "Products"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {hasQuery ? "Product search will appear here when the catalog is connected." : "Search to begin building your cart."}
              </p>
            </div>
          </div>

          {productResults.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-16 text-center">
              <SearchIcon className="mx-auto h-8 w-8 text-muted-foreground/60" aria-hidden="true" />
              <h3 className="mt-4 font-semibold">No products to show yet</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                {hasQuery
                  ? "Your search is ready. Results will appear here once product data is available."
                  : "Enter a grocery item above to search the catalog."}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {productResults.map((product) => (
                <article key={product.id} className="rounded-2xl border border-border bg-card p-5">
                  <p className="text-xs text-muted-foreground">{product.retailer}</p>
                  <h3 className="mt-3 font-semibold">{product.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{product.pack}</p>
                  <Button className="mt-5 w-full" disabled>
                    Add to cart
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
