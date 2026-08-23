import { create } from "zustand";

import type { CartItem } from "@/types/cart";
import type { Product } from "@/types/product";
import type { CartResolutionResult } from "@/types/cartResolution";
import type { CartCandidateDiscoveryResult } from "@/types/cartCandidates";
import type { CartOptimizationResult } from "@/types/cartOptimization";

interface CartStore {
  items: CartItem[];
  resolution: CartResolutionResult | null;
  candidateDiscovery: CartCandidateDiscoveryResult | null;
  optimizationResult: CartOptimizationResult | null;
  addItem: (product: Product) => void;
  removeItem: (itemId: string) => void;
  increaseQuantity: (itemId: string) => void;
  decreaseQuantity: (itemId: string) => void;
  clearCart: () => void;
  setResolution: (resolution: CartResolutionResult | null) => void;
  setCandidateDiscovery: (result: CartCandidateDiscoveryResult | null) => void;
  setOptimizationResult: (result: CartOptimizationResult | null) => void;
}

function itemIdForProduct(product: Product): string {
  return product.variantId ?? product.listingId ?? product.productId;
}

export const useCartStore = create<CartStore>((set) => ({
  items: [],
  resolution: null,
  candidateDiscovery: null,
  optimizationResult: null,

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
          candidateDiscovery: null,
          optimizationResult: null,
        };
      }

      return {
        items: [...state.items, { itemId, product, quantity: 1 }],
        resolution: null,
        candidateDiscovery: null,
        optimizationResult: null,
      };
    }),

  removeItem: (itemId) =>
    set((state) => ({
      items: state.items.filter((item) => item.itemId !== itemId),
      resolution: null,
      candidateDiscovery: null,
      optimizationResult: null,
    })),

  increaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.itemId === itemId ? { ...item, quantity: item.quantity + 1 } : item,
      ),
      resolution: null,
      candidateDiscovery: null,
      optimizationResult: null,
    })),

  decreaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items
        .map((item) =>
          item.itemId === itemId ? { ...item, quantity: item.quantity - 1 } : item,
        )
        .filter((item) => item.quantity > 0),
      resolution: null,
      candidateDiscovery: null,
      optimizationResult: null,
    })),

  clearCart: () => set({ items: [], resolution: null, candidateDiscovery: null, optimizationResult: null }),
  setResolution: (resolution) => set({ resolution, candidateDiscovery: null, optimizationResult: null }),
  setCandidateDiscovery: (candidateDiscovery) => set({ candidateDiscovery }),
  setOptimizationResult: (optimizationResult) => set({ optimizationResult }),
}));
