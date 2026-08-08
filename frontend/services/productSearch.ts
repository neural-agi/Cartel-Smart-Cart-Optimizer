import type { Product } from "@/types/product";

export type ProductSearchStatus = "unwired" | "ready";

export interface ProductSearchResult {
  query: string;
  status: ProductSearchStatus;
  products: readonly Product[];
}

export interface ProductSearchService {
  search(query: string): Promise<ProductSearchResult>;
}

/** Explicit boundary until a real Product Intelligence search endpoint exists. */
export const productSearchService: ProductSearchService = {
  async search(query) {
    return {
      query: query.trim(),
      status: "unwired",
      products: [],
    };
  },
};
