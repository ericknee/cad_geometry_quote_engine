import type { QuoteStatus } from "@/types";

/**
 * Status changes a reviewer may make, mirroring ALLOWED_TRANSITIONS in the API
 * (backend/api/services/quotes_service.py). The API still enforces them; this only decides
 * which controls to show. queued/processing/failed are set by the system, never by a reviewer.
 */
export const REVIEWER_MOVES: Record<QuoteStatus, readonly QuoteStatus[]> = {
  queued: [],
  processing: [],
  failed: ["archived"],
  quoted: ["reviewed", "archived"],
  reviewed: ["archived"],
  archived: [],
};

export const MOVE_LABELS: Partial<Record<QuoteStatus, string>> = {
  reviewed: "Mark reviewed",
  archived: "Archive",
};
