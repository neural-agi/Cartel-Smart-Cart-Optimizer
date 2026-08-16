import { create } from "zustand";

import type { CartItem } from "@/types/cart";
import type { Product } from "@/types/product";
import type { CartResolutionResult } from "@/types/cartResolution";

interface CartStore {
  items: CartItem[];
  resolution: CartResolutionResult | null;
  addItem: (product: Product) => void;
  removeItem: (itemId: string) => void;
  increaseQuantity: (itemId: string) => void;
  decreaseQuantity: (itemId: string) => void;
  clearCart: () => void;
  setResolution: (resolution: CartResolutionResult | null) => void;
}

function itemIdForProduct(product: Product): string {
  return product.variantId ?? product.listingId ?? product.productId;
}

export const useCartStore = create<CartStore>((set) => ({
  items: [],
  resolution: null,

  addItem: (product) =>
    set((state) => {
      const itemId = itemIdForProduct(product);
      const existing = state.items.find((item) => item.itemId === itemId);

      if (existing) {
        return {
          items: state.items.map((item) =>
            item.itemId === itemId ? { ...item, quantity: item.quantity + 1 } : item,
          ),
          resolution: null,
        };
      }

      return { items: [...state.items, { itemId, product, quantity: 1 }], resolution: null };
    }),

  removeItem: (itemId) =>
    set((state) => ({ items: state.items.filter((item) => item.itemId !== itemId), resolution: null })),

  increaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.itemId === itemId ? { ...item, quantity: item.quantity + 1 } : item,
      ),
      resolution: null,
    })),

  decreaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items
        .map((item) =>
          item.itemId === itemId ? { ...item, quantity: item.quantity - 1 } : item,
        )
        .filter((item) => item.quantity > 0),
      resolution: null,
    })),

  clearCart: () => set({ items: [], resolution: null }),
  setResolution: (resolution) => set({ resolution }),
}));
