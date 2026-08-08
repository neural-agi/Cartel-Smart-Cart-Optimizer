import { create } from "zustand";

import type { CartItem } from "@/types/cart";
import type { Product } from "@/types/product";

interface CartStore {
  items: CartItem[];
  addItem: (product: Product) => void;
  removeItem: (itemId: string) => void;
  increaseQuantity: (itemId: string) => void;
  decreaseQuantity: (itemId: string) => void;
  clearCart: () => void;
}

function itemIdForProduct(product: Product): string {
  return product.variantId ?? product.listingId ?? product.productId;
}

export const useCartStore = create<CartStore>((set) => ({
  items: [],

  addItem: (product) =>
    set((state) => {
      const itemId = itemIdForProduct(product);
      const existing = state.items.find((item) => item.itemId === itemId);

      if (existing) {
        return {
          items: state.items.map((item) =>
            item.itemId === itemId ? { ...item, quantity: item.quantity + 1 } : item,
          ),
        };
      }

      return { items: [...state.items, { itemId, product, quantity: 1 }] };
    }),

  removeItem: (itemId) =>
    set((state) => ({ items: state.items.filter((item) => item.itemId !== itemId) })),

  increaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.itemId === itemId ? { ...item, quantity: item.quantity + 1 } : item,
      ),
    })),

  decreaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items
        .map((item) =>
          item.itemId === itemId ? { ...item, quantity: item.quantity - 1 } : item,
        )
        .filter((item) => item.quantity > 0),
    })),

  clearCart: () => set({ items: [] }),
}));
