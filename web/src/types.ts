/**
 * The one place to import types from. API shapes are hand-copied from the backend's pydantic models
 * (backend/api/types/quotes_types.py, geometry/models.py, pricing/models.py); client-only types live here too.
 */

// queued -> processing -> quoted | failed, then a reviewer sets reviewed / archived.
export type QuoteStatus =
  | "queued"
  | "processing"
  | "failed"
  | "quoted"
  | "reviewed"
  | "archived";

export const ALL_STATUSES: readonly QuoteStatus[] = [
  "queued",
  "processing",
  "failed",
  "quoted",
  "reviewed",
  "archived",
];

/** Statuses still being worked on by the worker; the client polls while the quote is in one. */
export const IN_PROGRESS_STATUSES: readonly QuoteStatus[] = ["queued", "processing"];

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface BoundingBox {
  length: number;
  width: number;
  height: number;
}

export interface Features {
  face_count: number;
  edge_count: number;
  cylindrical_faces: number;
  holes_detected: number;
  setups: number;
  thin_wall_count: number;
  sa_to_volume_ratio: number;
  material_removal_ratio: number;
  complexity_score: number | null;
}

export interface GeometryResult {
  file: string;
  units: string;
  source_units: string | null;
  bounding_box_mm: BoundingBox;
  stock_volume_cm3: number;
  volume_cm3: number;
  surface_area_cm2: number;
  features: Features;
  solids: number;
  warnings: string[];
}

export interface MaterialCost {
  stock_volume_cm3: number;
  part_volume_cm3: number;
  removed_volume_cm3: number;
  computed_cost_unit: number;
  computed_cost_order: number;
  minimum_charge: number;
  minimum_applied: boolean;
  cost_unit: number;
  cost_order: number;
}

export interface MachineCost {
  roughing_minutes: number;
  hole_minutes: number;
  edge_minutes: number;
  thin_wall_count: number;
  mrr_cm3_per_min: number;
  cycle_minutes: number;
  cost_unit: number;
  cost_order: number;
}

export interface SetupCost {
  setups: number;
  setup_hours: number;
  cost_unit: number;
  cost_order: number;
}

export interface CostBreakdown {
  quantity: number;
  pricing_version: string;
  material: MaterialCost;
  machine: MachineCost;
  setup: SetupCost;
  total_cost_per_unit: number;
  total_order_cost: number;
}

export interface LeadTime {
  total_machine_hours: number;
  productive_hours_per_day: number;
  work_days: number;
  complexity_buffer_days: number;
  min_lead_time_days: number;
  days: number;
}

/** Geometry, cost and lead time exist only once quoted; `error` only when failed. */
export interface QuoteDetail {
  id: string;
  file_name: string;
  file_hash: string;
  quantity: number;
  material: string;
  status: QuoteStatus;
  geometry: GeometryResult | null;
  cost_breakdown: CostBreakdown | null;
  lead_time: LeadTime | null;
  lead_time_days: number | null;
  error: ErrorDetail | null;
  created_at: string;
  updated_at: string;
}

/** One dashboard row. */
export interface QuoteSummary {
  id: string;
  file_name: string;
  quantity: number;
  status: QuoteStatus;
  total_cost_per_unit: number | null;
  total_order_cost: number | null;
  lead_time_days: number | null;
  created_at: string;
  updated_at: string;
}

export interface QuoteList {
  items: QuoteSummary[];
  total: number;
  limit: number;
  skip: number;
}
