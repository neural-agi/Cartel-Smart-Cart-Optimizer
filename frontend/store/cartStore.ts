import { create } from "zustand";

import type { CartItem } from "@/types/cart";
import type { Product } from "@/types/product";
import type { CartResolutionResult } from "@/types/cartResolution";
import type { CartCandidateDiscoveryResult } from "@/types/cartCandidates";
import type { CartOptimizationResult } from "@/types/cartOptimization";
import type { AutomaticPlanningResult } from "@/types/automaticPlanning";

interface CartStore {
  items: CartItem[];
  resolution: CartResolutionResult | null;
  candidateDiscovery: CartCandidateDiscoveryResult | null;
  optimizationResult: CartOptimizationResult | null;
  automaticPlanning: AutomaticPlanningResult | null;
  addItem: (product: Product) => void;
  updateQuantity: (itemId: string, quantity: number) => void;
  removeItem: (itemId: string) => void;
  increaseQuantity: (itemId: string) => void;
  decreaseQuantity: (itemId: string) => void;
  clearCart: () => void;
  setResolution: (resolution: CartResolutionResult | null) => void;
  setCandidateDiscovery: (result: CartCandidateDiscoveryResult | null) => void;
  setOptimizationResult: (result: CartOptimizationResult | null) => void;
  setAutomaticPlanning: (result: AutomaticPlanningResult | null) => void;
}

function itemIdForProduct(product: Product): string {
  return product.variantId ?? product.listingId ?? product.productId;
}

export const useCartStore = create<CartStore>((set) => ({
  items: [],
  resolution: null,
  candidateDiscovery: null,
  optimizationResult: null,
  automaticPlanning: null,

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
          automaticPlanning: null,
        };
      }

      return {
        items: [...state.items, { itemId, product, quantity: 1 }],
        resolution: null,
        candidateDiscovery: null,
        optimizationResult: null,
        automaticPlanning: null,
      };
    }),

  removeItem: (itemId) =>
    set((state) => ({
      items: state.items.filter((item) => item.itemId !== itemId),
      resolution: null,
      candidateDiscovery: null,
      optimizationResult: null,
      automaticPlanning: null,
    })),

  increaseQuantity: (itemId) =>
    set((state) => ({
      items: state.items.map((item) =>
        item.itemId === itemId ? { ...item, quantity: item.quantity + 1 } : item,
      ),
      resolution: null,
      candidateDiscovery: null,
      optimizationResult: null,
      automaticPlanning: null,
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
      automaticPlanning: null,
    })),

  updateQuantity: (itemId, quantity) =>
    set((state) => ({
      items: quantity > 0
        ? state.items.map((item) => item.itemId === itemId ? { ...item, quantity: Math.floor(quantity) } : item)
        : state.items.filter((item) => item.itemId !== itemId),
      resolution: null,
      candidateDiscovery: null,
      optimizationResult: null,
      automaticPlanning: null,
    })),

  clearCart: () => set({ items: [], resolution: null, candidateDiscovery: null, optimizationResult: null, automaticPlanning: null }),
  setResolution: (resolution) => set({ resolution, candidateDiscovery: null, optimizationResult: null, automaticPlanning: null }),
  setCandidateDiscovery: (candidateDiscovery) => set({ candidateDiscovery }),
  setOptimizationResult: (optimizationResult) => set({ optimizationResult }),
  setAutomaticPlanning: (automaticPlanning) => set({ automaticPlanning, optimizationResult: automaticPlanning?.optimization_result ?? null }),
}));
