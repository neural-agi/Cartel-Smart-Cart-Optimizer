import type { Product } from "@/types/product";
import { apiFetch, readApiPayload, safeApiError } from "@/lib/apiClient";

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
      "observation_id",
      "evidence_state",
      "observed_at",
      "parser_version",
      "normalization_version",
      "source_reference",
      "raw_artifact_id",
      "raw_content_digest",
    ];
    if (required.some((field) => typeof candidate[field] !== "string" || !candidate[field])) {
      throw new Error(`Product search returned incomplete item at position ${index}.`);
    }
    if (candidate.evidence_state !== "registered_governed_observation"
      || typeof candidate.observed_at !== "string"
      || Number.isNaN(Date.parse(candidate.observed_at))) {
      throw new Error(`Product search returned unverified evidence at position ${index}.`);
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
      observationId: candidate.observation_id as string,
      name: candidate.canonical_display_name as string,
      brand: typeof candidate.brand === "string" ? candidate.brand : undefined,
      pack: typeof candidate.pack === "string" ? candidate.pack : undefined,
      platform: candidate.platform as string,
      price,
      availability: typeof candidate.availability_signal === "string"
        ? candidate.availability_signal
        : undefined,
      evidenceState: candidate.evidence_state,
      observedAt: typeof candidate.observed_at === "string" ? candidate.observed_at : undefined,
      parserVersion: typeof candidate.parser_version === "string" ? candidate.parser_version : undefined,
      normalizationVersion: typeof candidate.normalization_version === "string" ? candidate.normalization_version : undefined,
      retailerProductId: typeof candidate.retailer_product_id === "string" ? candidate.retailer_product_id : undefined,
      retailerProductUrl: typeof candidate.retailer_product_url === "string" ? candidate.retailer_product_url : undefined,
      sourceReference: candidate.source_reference as string,
      rawArtifactId: candidate.raw_artifact_id as string,
      rawContentDigest: candidate.raw_content_digest as string,
      evidenceReferences: Array.isArray(candidate.evidence_references)
        ? candidate.evidence_references.flatMap((reference) => {
            if (!reference || typeof reference !== "object") return [];
            const value = reference as Record<string, unknown>;
            if (typeof value.source_type !== "string" || typeof value.source_id !== "string") return [];
            return [{ sourceType: value.source_type, sourceId: value.source_id }];
          })
        : [],
      variantAttributes: Array.isArray(candidate.variant_attributes)
        ? candidate.variant_attributes.flatMap((attribute) => {
            if (!attribute || typeof attribute !== "object") return [];
            const value = attribute as Record<string, unknown>;
            if (["name", "value", "role", "assertion_status"].some((key) => typeof value[key] !== "string")) return [];
            return [{ name: value.name as string, value: value.value as string, role: value.role as string, assertionStatus: value.assertion_status as string }];
          })
        : [],
      identityAttributes: Array.isArray(candidate.identity_attributes)
        ? candidate.identity_attributes.flatMap((attribute) => {
            if (!attribute || typeof attribute !== "object") return [];
            const value = attribute as Record<string, unknown>;
            if (["name", "value", "role", "assertion_status"].some((key) => typeof value[key] !== "string")) return [];
            return [{ name: value.name as string, value: value.value as string, role: value.role as string, assertionStatus: value.assertion_status as string }];
          })
        : [],
    } satisfies Product;
  });

  return { query: body.query, status: "ready", products };
}

export const productSearchService: ProductSearchService = {
  async search(query) {
    const normalizedQuery = query.trim();
    const response = await apiFetch(
      `/api/v2/products/search?query=${encodeURIComponent(normalizedQuery)}`,
    );
    if (!response.ok) {
      const body = await readApiPayload<{ detail?: unknown }>(response);
      throw new Error(safeApiError(response, typeof body?.detail === "string" ? body.detail : "Product search is unavailable right now."));
    }
    return parseProductSearchResponse(await readApiPayload(response));
  },
};
