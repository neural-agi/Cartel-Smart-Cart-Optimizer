import type { CartItem } from "@/types/cart";
import type {
  AutomaticPlanningRequest,
  AutomaticPlanningResult,
} from "@/types/automaticPlanning";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function parseResult(value: unknown): AutomaticPlanningResult {
  if (!value || typeof value !== "object") {
    throw new Error("Automatic planning returned an invalid response.");
  }
  const body = value as Record<string, unknown>;
  if (
    typeof body.request_id !== "string" ||
    (body.status !== "ready" && body.status !== "unresolved") ||
    !Array.isArray(body.unresolved_reasons) ||
    (body.optimization_result !== null && typeof body.optimization_result !== "object")
  ) {
    throw new Error("Automatic planning returned an invalid response.");
  }
  return {
    request_id: body.request_id,
    status: body.status,
    optimization_result: body.optimization_result as AutomaticPlanningResult["optimization_result"],
    unresolved_reasons: body.unresolved_reasons.filter((reason): reason is string => typeof reason === "string"),
  };
}

export function automaticPlanningPayload(items: CartItem[]): AutomaticPlanningRequest {
  return {
    cart_id: "browser-cart",
    items: items.map((item) => ({
      item_id: item.itemId,
      canonical_product_id: item.product.productId,
      canonical_variant_id: item.product.variantId ?? "",
      quantity: item.quantity,
    })),
  };
}

export async function optimizeCart(items: CartItem[]): Promise<AutomaticPlanningResult> {
  const payload = automaticPlanningPayload(items);
  const response = await fetch(`${API_BASE_URL}/api/v1/cart/optimize`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = `Automatic planning failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the HTTP failure when the response is not JSON.
    }
    throw new Error(message);
  }
  return parseResult(await response.json());
}
