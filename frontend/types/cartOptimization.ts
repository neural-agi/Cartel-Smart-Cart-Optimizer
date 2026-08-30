export type OptimizationOutcome = "selected" | "infeasible" | "unresolved";
export type PlanFeasibility = "feasible" | "infeasible" | "unresolved" | "invalid";

export interface OptimizationConstraintReference {
  optimization_constraint_id: string;
}

export interface ItemAllocation {
  item_id: string;
  canonical_variant_id: string;
  quantity: number;
  retailer_id: string;
  checkout_group_id: string;
}

export interface RetailerAllocation {
  retailer_id: string;
  checkout_group_id: string;
}

export interface CheckoutGroup {
  checkout_group_id: string;
  retailer_id: string;
  effective_cost_evaluation_id: string;
}

export interface CandidatePlan {
  plan_id: string;
  inconvenience_penalty_units: number;
  retailer_preference_priority: number;
  retailer_allocations: RetailerAllocation[];
  item_allocations: ItemAllocation[];
  candidate_item_allocations?: Array<ItemAllocation & {
    listing_provenance?: {
      platform: string;
      platform_listing_id: string;
      observation_id: string;
      observed_selling_price?: { currency: string; minor_units: number };
    };
  }>;
  checkout_groups: CheckoutGroup[];
  effective_cost_evaluation_reference: {
    effective_cost_evaluation_id: string;
  };
  feasibility: PlanFeasibility;
  unknown_components: string[];
  provenance_references: Array<{ source_type: string; source_id: string }>;
}

export interface RejectedPlan {
  plan_id: string;
  code: string;
  explanation: string | null;
}

export interface CartOptimizationResult {
  optimization_id: string;
  request_id: string;
  chosen_plan_id: string | null;
  chosen_plan: CandidatePlan | null;
  outcome: OptimizationOutcome;
  rationale: string[];
  unknowns: string[];
  assumptions: string[];
  provenance_references: Array<{ source_type: string; source_id: string }>;
  ranked_plan_ids: string[];
  alternative_plans: CandidatePlan[];
  rejected_plans: RejectedPlan[];
  rejection_reasons: string[];
}
