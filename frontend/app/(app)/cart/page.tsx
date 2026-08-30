"use client";

import { useRouter } from "next/navigation";
import { Minus, Plus, ShoppingCart, Trash2 } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { useCartStore } from "@/store/cartStore";

export default function CartPage() {
  const router = useRouter();
  const items = useCartStore((state) => state.items);
  const increaseQuantity = useCartStore((state) => state.increaseQuantity);
  const decreaseQuantity = useCartStore((state) => state.decreaseQuantity);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const removeItem = useCartStore((state) => state.removeItem);
  const clearCart = useCartStore((state) => state.clearCart);

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
                  <article key={item.itemId} className="flex items-center justify-between gap-4 py-5">
                    <div className="min-w-0">
                      <h3 className="truncate font-medium">{item.product.name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">{item.product.pack ?? "Pack information unavailable"}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button variant="outline" size="icon-sm" aria-label={`Decrease ${item.product.name} quantity`} onClick={() => decreaseQuantity(item.itemId)}>
                        <Minus className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <input
                        aria-label={`Quantity for ${item.product.name}`}
                        type="number"
                        min={1}
                        step={1}
                        value={item.quantity}
                        onChange={(event) => updateQuantity(item.itemId, Number(event.target.value))}
                        className="h-8 w-14 rounded-md border border-border bg-background text-center text-sm"
                      />
                      <Button variant="outline" size="icon-sm" aria-label={`Increase ${item.product.name} quantity`} onClick={() => increaseQuantity(item.itemId)}>
                        <Plus className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" aria-label={`Remove ${item.product.name}`} onClick={() => removeItem(item.itemId)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <aside className="h-fit rounded-2xl border border-border bg-card p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold">Cart summary</h2>
                <Button variant="ghost" size="sm" onClick={clearCart}>Clear cart</Button>
              </div>
              <div className="mt-5 flex items-center justify-between border-t border-border pt-4 text-sm">
                <span className="text-muted-foreground">Subtotal</span>
                <span>To be calculated</span>
              </div>
              <Button className="mt-5 w-full" onClick={() => router.push("/optimize")}>
                Optimize cart
              </Button>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">
                Optimization uses only governed candidate and checkout data. Missing authority is reported instead of estimated.
              </p>
            </aside>
          </div>
        )}
      </div>
    </AppShell>
  );
}
