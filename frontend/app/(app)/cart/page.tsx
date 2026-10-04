"use client";

import { useRouter } from "next/navigation";
import { ShoppingCart, Trash2 } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { useCartStore } from "@/store/cartStore";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";
import QuantityControl from "@/components/consumer/QuantityControl";

export default function CartPage() {
  const router = useRouter();
  const items = useCartStore((state) => state.items);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const removeItem = useCartStore((state) => state.removeItem);
  const clearCart = useCartStore((state) => state.clearCart);

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader eyebrow="Current cart" title="Your groceries, in one place." description="Review your saved product choices before comparing the supported ways Cartel can buy them." />

        {items.length === 0 ? (
          <StatePanel icon={ShoppingCart} title="Your cart is empty" description="Search for a verified product and add it here to begin a comparison." action={<Button onClick={() => router.push("/search")}>Search products</Button>} />
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
                      <QuantityControl label={item.product.name} value={item.quantity} onChange={(quantity) => updateQuantity(item.itemId, quantity)} />
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
                Optimization uses only verified product information and supported checkout data. Missing information is reported instead of estimated.
              </p>
            </aside>
          </div>
        )}
      </div>
    </AppShell>
  );
}
