export interface ShoppingListItem {
  id: string;
  query: string;
  quantity: number;
  unit: string | null;
  resolution_status: "unresolved" | "exact_confirmed";
  canonical_product_id: string | null;
  canonical_variant_id: string | null;
  display_name: string | null;
  source_platform: string | null;
  source_listing_id: string | null;
  source_observation_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShoppingList {
  id: string;
  name: string;
  revision: number;
  archived: boolean;
  created_at: string;
  updated_at: string;
  items: readonly ShoppingListItem[];
}

export interface ShoppingListItemInput {
  query: string;
  quantity?: number;
  unit?: string;
  canonical_product_id?: string;
  canonical_variant_id?: string;
  source_platform?: string;
  source_listing_id?: string;
  source_observation_id?: string;
}
