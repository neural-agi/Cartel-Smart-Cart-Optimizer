export type CartItemResolutionStatus = "resolved" | "unresolved";

export interface CartResolutionRequestItem {
  item_id: string;
  quantity: number;
  canonical_variant_id?: string;
  platform?: string;
  platform_listing_id?: string;
}

export interface CartResolutionRequest {
  items: CartResolutionRequestItem[];
}

export interface CartItemResolution {
  item_id: string;
  quantity: number;
  status: CartItemResolutionStatus;
  reason: string | null;
  canonical_product_id: string | null;
  canonical_variant_id: string | null;
  platform: string | null;
  platform_listing_id: string | null;
  observation_id: string | null;
  observation: unknown | null;
}

export interface CartResolutionResult {
  items: CartItemResolution[];
}
