export type CartCandidateDiscoveryStatus =
  | "candidates_available"
  | "candidates_not_ready"
  | "no_candidates";

export type PersistedCandidateReadiness =
  | "ready_for_allocation"
  | "not_ready_for_allocation";

export interface CartCandidateDiscoveryRequestItem {
  item_id: string;
  quantity: number;
  canonical_product_id: string;
  canonical_variant_id: string;
}

export interface CartCandidateDiscoveryRequest {
  items: CartCandidateDiscoveryRequestItem[];
}

export interface PersistedListingCandidate {
  platform: string;
  platform_listing_id: string;
  canonical_product_id: string;
  canonical_variant_id: string;
  observation_id: string;
  observation: unknown;
  readiness: PersistedCandidateReadiness;
  readiness_reason: string | null;
}

export interface CartCandidateDiscoveryItem {
  item_id: string;
  quantity: number;
  canonical_product_id: string;
  canonical_variant_id: string;
  status: CartCandidateDiscoveryStatus;
  reason: string | null;
  candidates: PersistedListingCandidate[];
}

export interface CartCandidateDiscoveryResult {
  items: CartCandidateDiscoveryItem[];
}
