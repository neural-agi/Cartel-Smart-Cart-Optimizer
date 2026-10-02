import { apiFetch } from "@/lib/apiClient";
import type { ShoppingList, ShoppingListItemInput } from "@/types/shoppingLists";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Shopping list request failed (${response.status}).`;
    try {
      const body = await response.json() as { detail?: { code?: string; message?: string } | string };
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail?.message) message = body.detail.message;
      else if (body.detail?.code) message = body.detail.code.replaceAll("_", " ");
    } catch {
      // Keep the status-based message for a non-JSON failure.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

export const shoppingListsService = {
  async list(): Promise<readonly ShoppingList[]> {
    return parseResponse(await apiFetch("/api/v2/lists", { cache: "no-store" }));
  },

  async create(name: string): Promise<ShoppingList> {
    return parseResponse(await apiFetch("/api/v2/lists", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

  async addItem(listId: string, item: ShoppingListItemInput): Promise<ShoppingList> {
    return parseResponse(await apiFetch(`/api/v2/lists/${encodeURIComponent(listId)}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
