"""Every pricing constant in one place, so calibration only touches this file (FR-P)."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PricingConfig(BaseModel):
    # Frozen: a config cannot change while a quote is being priced.
    model_config = ConfigDict(frozen=True)

    # Bump when any value changes, so stored quotes stay explainable.
    pricing_version: str = "v1-draft"

    # Given by the PRD: 6061 aluminum on a Haas CNC.
    density_g_per_cm3: float = Field(default=2.7, gt=0)
    material_price_per_kg: float = Field(default=5.0, gt=0)
    machine_rate_per_hour: float = Field(default=100.0, gt=0)
    # Minimum stock purchase and saw cuts make tiny parts cost more than their volume.
    min_material_charge: float = Field(default=10.0, ge=0)

    # Machine time. Placeholders, tuned against competitor quotes.
    roughing_cm3_per_min: float = Field(default=1.0, gt=0)
    finishing_cm2_per_min: float = Field(default=1.0, gt=0)
    minutes_per_hole: float = Field(default=2.0, ge=0)
    handling_minutes: float = Field(default=3.0, ge=0)
    # Used when the geometry has no complexity score yet.
    default_complexity_score: float = Field(default=1.0, ge=1.0, le=3.0)

    # setup_hours = base x (1 + extra_per_setup x (setups - 1)); base set so the gear is ~1.4 h.
    base_setup_hours: float = Field(default=1.12, ge=0)
    setup_extra_per_setup: float = Field(default=0.25, ge=0)

    # (minimum quantity, discount on machine cost), ascending. Qty 100 is in the 20% tier.
    discount_tiers: tuple[tuple[int, float], ...] = (
        (1, 0.0),
        (6, 0.10),
        (21, 0.20),
        (101, 0.30),
    )

    # Lead time (business days).
    min_lead_time_days: int = Field(default=5, ge=0)
    productive_hours_per_day: float = Field(default=8.0, gt=0)
    # (minimum complexity score, extra days), ascending. Placeholder: no extra days until the
    # complexity score exists.
    complexity_buffer_bands: tuple[tuple[float, int], ...] = ((1.0, 0),)

    @model_validator(mode="after")
    def _check_tables(self) -> "PricingConfig":
        quantities = [q for q, _ in self.discount_tiers]
        if not quantities or quantities[0] != 1 or quantities != sorted(set(quantities)):
            raise ValueError("discount_tiers must start at quantity 1 and strictly ascend")
        if any(not 0 <= rate <= 1 for _, rate in self.discount_tiers):
            raise ValueError("discount rates must be between 0 and 1")
        scores = [s for s, _ in self.complexity_buffer_bands]
        if not scores or scores[0] > 1.0 or scores != sorted(set(scores)):
            raise ValueError("complexity_buffer_bands must cover score 1.0 and strictly ascend")
        return self
