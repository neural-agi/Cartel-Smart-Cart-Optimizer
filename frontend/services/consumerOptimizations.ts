import { apiFetch, newIdempotencyKey, readApiPayload, safeApiError } from "@/lib/apiClient";
import type { ConsumerOptimizationResult } from "@/types/consumerOptimization";

async function parse(response: Response): Promise<ConsumerOptimizationResult> {
  if (!response.ok) {
    const body = await readApiPayload<{ detail?: string }>(response);
    throw new Error(safeApiError(response, body?.detail ?? "Cartel could not complete this comparison."));
  }
  return await readApiPayload<ConsumerOptimizationResult>(response) as ConsumerOptimizationResult;
}

export const consumerOptimizations = {
  async create(listId: string, revision: number, key = newIdempotencyKey()): Promise<ConsumerOptimizationResult> {
    return parse(await apiFetch("/api/v2/optimizations", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": key },
      body: JSON.stringify({ list_id: listId, expected_revision: revision }),
    }));
  },
  async get(requestId: string): Promise<ConsumerOptimizationResult> {
    return parse(await apiFetch(`/api/v2/optimizations/${encodeURIComponent(requestId)}`, { cache: "no-store" }));
  },
};
