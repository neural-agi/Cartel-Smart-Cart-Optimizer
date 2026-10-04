export interface ConsumerOptimizationMoney {
  currency: string;
  minor_units: number;
}

export interface ConsumerOptimizationOffer {
  item_id: string;
  canonical_product_id: string;
  canonical_variant_id: string;
  quantity: number;
  platform: string;
  retailer_id: string | null;
  platform_listing_id: string;
  observation_id: string;
  observed_unit_price: ConsumerOptimizationMoney;
  observed_product_subtotal: ConsumerOptimizationMoney;
  observed_at: string;
  parser_version: string;
  normalization_version: string;
  availability: string;
  observation_state: "latest_governed_observation";
  source_reference: string;
}

export interface ConsumerOptimizationItem {
  item_id: string;
  query: string;
  quantity: number;
  resolution_status: "unresolved" | "exact_confirmed";
  canonical_product_id: string | null;
  canonical_variant_id: string | null;
  source_platform: string | null;
  source_listing_id: string | null;
  source_observation_id: string | null;
}

export interface ConsumerOptimizationResult {
  request_id: string;
  list_id: string;
  list_revision: number;
  input_digest: string;
  policy_version: string;
  status: "ready" | "unresolved" | "unavailable" | "infeasible" | "no_plan";
  completeness: "complete" | "partial" | "unavailable";
  created_at: string | null;
  requested_items: readonly ConsumerOptimizationItem[];
  offers: readonly ConsumerOptimizationOffer[];
  unresolved_items: readonly ConsumerOptimizationItem[];
  optimizer_result: Record<string, unknown> | null;
  explanation: string;
}
