"""Every pricing constant in one place, so calibration only touches this file (FR-P)."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PricingConfig(BaseModel):
    # Frozen: a config cannot change while a quote is being priced.
    model_config = ConfigDict(frozen=True)

    # Bump when any value changes, so stored quotes stay explainable.
    pricing_version: str = "v2-draft"

    # Density, $/kg and machine rate come from the Material (geometry/materials.py), not here.
    # Per ORDER: minimum stock purchase and saw cuts make small orders cost more than their volume.
    min_material_charge: float = Field(default=10.0, ge=0)

    # Machine time. Assumptions, not measured; stated in the README and REPORT.
    # Roughing: material removal rate (MRR), cm3 of metal cut per minute. One constant for 6061.
    roughing_cm3_per_min: float = Field(default=50.0, gt=0)
    minutes_per_hole: float = Field(default=2.0, ge=0)
    # Assumption: the machine slows and re-accelerates where the tool path changes direction, so
    # every edge in the part adds a little time. Not measured; 0.05 min = 3 s per edge.
    minutes_per_edge: float = Field(default=0.05, ge=0)
    # Cap on the edge time per unit, so a part with thousands of edges is not priced by edge
    # count alone. Assumption; 60 min = 1 hour.
    max_edge_minutes: float = Field(default=60.0, ge=0)
    # Thin walls (under 3 mm, counted by the geometry engine) force lighter cuts, so they lower
    # the MRR in even steps from the base rate down to the minimum: 0 thin walls = base rate,
    # `thin_walls_for_min_mrr` or more = the minimum.
    #   MRR = base - (base - minimum) x min(thin_walls, full) / full
    min_roughing_cm3_per_min: float = Field(default=20.0, gt=0)
    thin_walls_for_min_mrr: int = Field(default=8, ge=1)

    # Setup is a one-time cost per order, built from two parts. The log2-face value (0.19) is
    # fitted to the gear quote (qty 1 ~ $193, competitors $190-195); the others are assumptions.
    # setup_hours = programming + setups x fixture
    #   programming = programming_base + programming_per_log2_face x log2(faces)
    fixture_hours_per_setup: float = Field(default=0.1, ge=0)  # clamp and zero, per clamping
    programming_base_hours: float = Field(default=0.1, ge=0)  # CAM work any part needs
    # More faces means more tool paths to program. Log scale: the 10th face adds far more
    # work than the 100th.
    programming_hours_per_log2_face: float = Field(default=0.19, ge=0)

    # Lead time (business days).
    min_lead_time_days: int = Field(default=5, ge=0)
    productive_hours_per_day: float = Field(default=8.0, gt=0)
    # Complexity buffer: a safety margin for programming, fixturing and inspection, not cutting.
    # Assumptions, not measured. Complexity = min(faces / buffer_full_faces, 1), and
    #   buffer days = ceil(machine days x max_buffer_rate x complexity)
    # so a part with `buffer_full_faces` or more faces gets the full rate. 100 faces is a guess
    # from two samples (bracket 17, gear 99).
    buffer_full_faces: int = Field(default=100, ge=1)
    max_buffer_rate: float = Field(default=0.5, ge=0)

    @model_validator(mode="after")
    def _check_tables(self) -> "PricingConfig":
        if self.min_roughing_cm3_per_min > self.roughing_cm3_per_min:
            raise ValueError("min_roughing_cm3_per_min must not exceed roughing_cm3_per_min")
        return self
