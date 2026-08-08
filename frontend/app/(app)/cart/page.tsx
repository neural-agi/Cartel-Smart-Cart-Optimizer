"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Minus, Plus, ShoppingCart, Trash2 } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";

interface CartItem {
  id: string;
  name: string;
  pack: string;
  quantity: number;
  unitPriceMinorUnits?: number;
}

const initialItems: CartItem[] = [];

export default function CartPage() {
  const router = useRouter();
  const [items, setItems] = useState<CartItem[]>(initialItems);

  const updateQuantity = (id: string, change: number) => {
    setItems((currentItems) =>
      currentItems
        .map((item) => (item.id === id ? { ...item, quantity: item.quantity + change } : item))
        .filter((item) => item.quantity > 0),
    );
  };

  const removeItem = (id: string) => {
    setItems((currentItems) => currentItems.filter((item) => item.id !== id));
  };

  return (
    <AppShell>
      <div className="space-y-8">
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Current cart</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Your groceries, in one place.</h1>
          <p className="max-w-2xl text-muted-foreground">
            Review your items before comparing the ways to buy them.
          </p>
        </header>

        {items.length === 0 ? (
          <section className="rounded-2xl border border-dashed border-border bg-card/50 px-6 py-20 text-center">
            <ShoppingCart className="mx-auto h-9 w-9 text-muted-foreground/60" aria-hidden="true" />
            <h2 className="mt-5 text-lg font-semibold">Your cart is empty</h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
              Search for groceries and add them here when product data is connected.
            </p>
            <Button className="mt-6" onClick={() => router.push("/search")}>
              Search products
            </Button>
          </section>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <section aria-labelledby="cart-items-heading" className="space-y-4">
              <h2 id="cart-items-heading" className="text-lg font-semibold">Cart items</h2>
              <div className="divide-y divide-border rounded-2xl border border-border bg-card px-5">
                {items.map((item) => (
                  <article key={item.id} className="flex items-center justify-between gap-4 py-5">
                    <div className="min-w-0">
                      <h3 className="truncate font-medium">{item.name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">{item.pack}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button variant="outline" size="icon-sm" aria-label={`Decrease ${item.name} quantity`} onClick={() => updateQuantity(item.id, -1)}>
                        <Minus className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <span className="w-6 text-center text-sm font-medium">{item.quantity}</span>
                      <Button variant="outline" size="icon-sm" aria-label={`Increase ${item.name} quantity`} onClick={() => updateQuantity(item.id, 1)}>
                        <Plus className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" aria-label={`Remove ${item.name}`} onClick={() => removeItem(item.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <aside className="h-fit rounded-2xl border border-border bg-card p-5">
              <h2 className="font-semibold">Cart summary</h2>
              <div className="mt-5 flex items-center justify-between border-t border-border pt-4 text-sm">
                <span className="text-muted-foreground">Subtotal</span>
                <span>To be calculated</span>
              </div>
              <Button className="mt-5 w-full" disabled>
                Optimize cart
              </Button>
            </aside>
          </div>
        )}
      </div>
    </AppShell>
  );
}
