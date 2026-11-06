import { ALL_STATUSES, type QuoteStatus } from "@/types";

export const PAGE_SIZE = 20;

export type SortOrder = "newest" | "oldest";

/** The dashboard's view of the list. It lives in the URL query string. */
export interface Filters {
  status: QuoteStatus | null;
  showArchived: boolean;
  sort: SortOrder;
  page: number; // 1-based
}

export const DEFAULT_FILTERS: Filters = {
  status: null,
  showArchived: false,
  sort: "newest",
  page: 1,
};

/** Reads filters from the URL. Anything invalid falls back to the default. */
export function parseFilters(params: URLSearchParams): Filters {
  const status = params.get("status") as QuoteStatus | null;
  const page = Number(params.get("page"));
  return {
    status: status && ALL_STATUSES.includes(status) ? status : null,
    showArchived: params.get("archived") === "1",
    sort: params.get("sort") === "oldest" ? "oldest" : "newest",
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  };
}

/** Query string for the filters; defaults are left out to keep URLs short. */
export function filtersToQuery(filters: Filters): string {
  const query = new URLSearchParams();
  if (filters.status) query.set("status", filters.status);
  if (filters.showArchived) query.set("archived", "1");
  if (filters.sort !== DEFAULT_FILTERS.sort) query.set("sort", filters.sort);
  if (filters.page > 1) query.set("page", String(filters.page));
  return query.toString();
}

/** Arguments for listQuotes. An explicit status wins over hiding archived, as in the API. */
export function toListParams(filters: Filters) {
  return {
    status: filters.status ?? undefined,
    excludeArchived: filters.status === null && !filters.showArchived,
    sort: filters.sort,
    limit: PAGE_SIZE,
    skip: (filters.page - 1) * PAGE_SIZE,
  };
}
