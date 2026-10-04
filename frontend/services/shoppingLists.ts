import { apiFetch, newIdempotencyKey, readApiPayload, safeApiError } from "@/lib/apiClient";
import type { ShoppingList, ShoppingListItemInput } from "@/types/shoppingLists";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await readApiPayload<{ detail?: { message?: string } | string }>(response);
    const detail = typeof body?.detail === "string" ? body.detail : body?.detail?.message;
    throw new Error(safeApiError(response, detail ?? "Shopping list is unavailable right now."));
  }
  if (response.status === 204) return undefined as T;
  return await readApiPayload<T>(response) as T;
}

export const shoppingListsService = {
  async get(listId: string): Promise<ShoppingList> {
    return parseResponse(await apiFetch(`/api/v2/lists/${encodeURIComponent(listId)}`, { cache: "no-store" }));
  },

  async list(): Promise<readonly ShoppingList[]> {
    return parseResponse(await apiFetch("/api/v2/lists", { cache: "no-store" }));
  },

  async create(name: string, key = newIdempotencyKey()): Promise<ShoppingList> {
    return parseResponse(await apiFetch("/api/v2/lists", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify({ name }),
    }));
  },

  async update(listId: string, change: { name?: string; archived?: boolean }): Promise<ShoppingList> {
    return parseResponse(await apiFetch(`/api/v2/lists/${encodeURIComponent(listId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(change),
    }));
  },

  async addItem(listId: string, item: ShoppingListItemInput, key = newIdempotencyKey()): Promise<ShoppingList> {
    return parseResponse(await apiFetch(`/api/v2/lists/${encodeURIComponent(listId)}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify(item),
    }));
  },

  async updateItem(listId: string, itemId: string, quantity: number): Promise<ShoppingList> {
    return parseResponse(await apiFetch(
      `/api/v2/lists/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}`,
      { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ quantity }) },
    ));
  },

  async removeItem(listId: string, itemId: string): Promise<void> {
    await parseResponse<void>(await apiFetch(
      `/api/v2/lists/${encodeURIComponent(listId)}/items/${encodeURIComponent(itemId)}`,
      { method: "DELETE" },
    ));
  },
};
