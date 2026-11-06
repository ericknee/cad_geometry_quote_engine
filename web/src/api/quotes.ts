/** Calls to the quotes endpoints. Each returns typed data or throws ApiError (see http.ts). */
import type { QuoteDetail, QuoteList, QuoteStatus } from "@/types";
import { request } from "./http";

export function createQuote(file: File, quantity: number): Promise<QuoteDetail> {
  const body = new FormData();
  body.append("file", file);
  body.append("quantity", String(quantity));
  return request<QuoteDetail>("/quotes", { method: "POST", body });
}

export function getQuote(id: string): Promise<QuoteDetail> {
  return request<QuoteDetail>(`/quotes/${id}`);
}

export function listQuotes(params: {
  status?: QuoteStatus;
  /** Hide archived quotes (ignored by the API when `status` is set). */
  excludeArchived?: boolean;
  /** By creation time; the API default is newest. */
  sort?: "newest" | "oldest";
  limit?: number;
  skip?: number;
}): Promise<QuoteList> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.excludeArchived) query.set("exclude_archived", "true");
  if (params.sort) query.set("sort", params.sort);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.skip !== undefined) query.set("skip", String(params.skip));
  const qs = query.toString();
  return request<QuoteList>(`/quotes${qs ? `?${qs}` : ""}`);
}

export function updateQuoteStatus(id: string, status: QuoteStatus): Promise<QuoteDetail> {
  return request<QuoteDetail>(`/quotes/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}
