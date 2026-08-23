import type { Product } from "@/types/product";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export type ProductSearchStatus = "ready";

export interface ProductSearchResult {
  query: string;
  status: ProductSearchStatus;
  products: readonly Product[];
}

export interface ProductSearchService {
  search(query: string): Promise<ProductSearchResult>;
}

function parseProductSearchResponse(value: unknown): ProductSearchResult {
  if (!value || typeof value !== "object") {
    throw new Error("Product search returned an invalid response.");
  }
  const body = value as { query?: unknown; items?: unknown };
  if (typeof body.query !== "string" || !Array.isArray(body.items)) {
    throw new Error("Product search returned an invalid response.");
  }

  const products = body.items.map((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error(`Product search returned an invalid item at position ${index}.`);
    }
    const candidate = item as Record<string, unknown>;
    const required = [
      "canonical_product_id",
      "canonical_variant_id",
      "canonical_display_name",
      "platform",
      "platform_listing_id",
    ];
    if (required.some((field) => typeof candidate[field] !== "string" || !candidate[field])) {
      throw new Error(`Product search returned incomplete item at position ${index}.`);
    }
    const rawPrice = candidate.price;
    const price = rawPrice === null || rawPrice === undefined
      ? undefined
      : (() => {
          if (!rawPrice || typeof rawPrice !== "object") throw new Error("Product price is malformed.");
          const value = rawPrice as Record<string, unknown>;
          if (typeof value.currency !== "string" || typeof value.minor_units !== "number") {
            throw new Error("Product price is malformed.");
          }
          return { currency: value.currency, minorUnits: value.minor_units };
        })();

    return {
      productId: candidate.canonical_product_id as string,
      variantId: candidate.canonical_variant_id as string,
      listingId: candidate.platform_listing_id as string,
      name: candidate.canonical_display_name as string,
      brand: typeof candidate.brand === "string" ? candidate.brand : undefined,
      pack: typeof candidate.pack === "string" ? candidate.pack : undefined,
      platform: candidate.platform as string,
      price,
      availability: typeof candidate.availability_signal === "string"
        ? candidate.availability_signal
        : undefined,
    } satisfies Product;
  });

  return { query: body.query, status: "ready", products };
}

export const productSearchService: ProductSearchService = {
  async search(query) {
    const normalizedQuery = query.trim();
    const response = await fetch(
      `${API_BASE_URL}/api/v1/products/search?query=${encodeURIComponent(normalizedQuery)}`,
    );
    if (!response.ok) {
      let message = `Product search failed with status ${response.status}`;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        // Preserve the HTTP failure when the response is not JSON.
      }
      throw new Error(message);
    }
    return parseProductSearchResponse(await response.json());
  },
};
