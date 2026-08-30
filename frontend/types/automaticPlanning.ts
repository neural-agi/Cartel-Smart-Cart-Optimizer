import type { CartOptimizationResult } from "./cartOptimization";

export interface AutomaticPlanningRequestItem {
  item_id: string;
  canonical_product_id: string;
  canonical_variant_id: string;
  quantity: number;
}

export interface AutomaticPlanningRequest {
  cart_id: string;
  items: AutomaticPlanningRequestItem[];
}

export type AutomaticPlanningStatus = "ready" | "unresolved";

export interface AutomaticPlanningResult {
  request_id: string;
  status: AutomaticPlanningStatus;
  optimization_result: CartOptimizationResult | null;
  unresolved_reasons: string[];
}
