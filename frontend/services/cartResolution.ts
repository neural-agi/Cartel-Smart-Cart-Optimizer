import type { CartItem } from "@/types/cart";
import type {
  CartResolutionRequest,
  CartResolutionRequestItem,
  CartResolutionResult,
} from "@/types/cartResolution";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class CartResolutionError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "CartResolutionError";
  }
}

function requestItemFromCartItem(item: CartItem): CartResolutionRequestItem {
  const requestItem: CartResolutionRequestItem = {
    item_id: item.itemId,
    quantity: item.quantity,
  };

  if (item.product.variantId) {
    requestItem.canonical_variant_id = item.product.variantId;
    return requestItem;
  }

  if (item.product.platform && item.product.listingId) {
    requestItem.platform = item.product.platform;
    requestItem.platform_listing_id = item.product.listingId;
    return requestItem;
  }

  throw new CartResolutionError(
    `Cart item ${item.itemId} has no canonical variant or platform listing identity`,
  );
}

export function buildCartResolutionRequest(items: CartItem[]): CartResolutionRequest {
  return { items: items.map(requestItemFromCartItem) };
}

export async function resolveCart(items: CartItem[]): Promise<CartResolutionResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/cart/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildCartResolutionRequest(items)),
  });

  if (!response.ok) {
    let message = `Cart resolution failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the HTTP failure when the response is not JSON.
    }
    throw new CartResolutionError(message, response.status);
  }

  return (await response.json()) as CartResolutionResult;
}
