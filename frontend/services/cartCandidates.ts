import type { CartItemResolution, CartResolutionResult } from "@/types/cartResolution";
import type {
  CartCandidateDiscoveryRequest,
  CartCandidateDiscoveryRequestItem,
  CartCandidateDiscoveryResult,
} from "@/types/cartCandidates";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class CartCandidateDiscoveryError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "CartCandidateDiscoveryError";
  }
}

function requestItemFromResolution(item: CartItemResolution): CartCandidateDiscoveryRequestItem | null {
  if (item.status !== "resolved") {
    return null;
  }

  if (!item.canonical_product_id || !item.canonical_variant_id) {
    throw new CartCandidateDiscoveryError(
      `Resolved cart item ${item.item_id} is missing canonical product or variant identity`,
    );
  }

  return {
    item_id: item.item_id,
    quantity: item.quantity,
    canonical_product_id: item.canonical_product_id,
    canonical_variant_id: item.canonical_variant_id,
  };
}

export function buildCartCandidateDiscoveryRequest(
  resolution: CartResolutionResult,
): CartCandidateDiscoveryRequest {
  return {
    items: resolution.items
      .map(requestItemFromResolution)
      .filter((item): item is CartCandidateDiscoveryRequestItem => item !== null),
  };
}

export async function discoverCartCandidates(
  resolution: CartResolutionResult,
): Promise<CartCandidateDiscoveryResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/cart/candidates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildCartCandidateDiscoveryRequest(resolution)),
  });

  if (!response.ok) {
    let message = `Cart candidate discovery failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the HTTP failure when the response is not JSON.
    }
    throw new CartCandidateDiscoveryError(message, response.status);
  }

  return (await response.json()) as CartCandidateDiscoveryResult;
}
