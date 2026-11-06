"""price(): geometry + quantity -> cost breakdown (FR-P1..P6). Pure: no I/O, no globals.

Everything is computed unrounded; money and intermediates are rounded only when the result
models are built, so rounding never feeds into another calculation.
"""

import math
from dataclasses import dataclass

from geometry.materials import get_material
from geometry.models import GeometryResult

from pricing.config import PricingConfig
from pricing.models import (
    CostBreakdown,
    MachineCost,
    MaterialCost,
    SetupCost,
)

_MONEY_DECIMALS = 2
_QUANTITY_DECIMALS = 3  # minutes, hours, volumes


@dataclass(frozen=True)
class Cycle:
    """Unrounded machine time for one part."""

    roughing_minutes: float
    hole_minutes: float
    edge_minutes: float
    mrr_cm3_per_min: float

    @property
    def minutes(self) -> float:
        return self.roughing_minutes + self.hole_minutes + self.edge_minutes


def cycle_time(geometry: GeometryResult, config: PricingConfig) -> Cycle:
    """FR-P2. Shared with the lead-time model."""
    features = geometry.features
    removed = max(0.0, geometry.stock_volume_cm3 - geometry.volume_cm3)
    mrr = effective_mrr(features.thin_wall_count, config)
    return Cycle(
        roughing_minutes=removed / mrr,
        hole_minutes=features.holes_detected * config.minutes_per_hole,
        edge_minutes=min(features.edge_count * config.minutes_per_edge, config.max_edge_minutes),
        mrr_cm3_per_min=mrr,
    )


def effective_mrr(thin_walls: int, config: PricingConfig) -> float:
    """MRR in cm3/min: falls linearly from the base rate to the minimum as thin walls rise."""
    share = min(thin_walls, config.thin_walls_for_min_mrr) / config.thin_walls_for_min_mrr
    base, minimum = config.roughing_cm3_per_min, config.min_roughing_cm3_per_min
    return base - (base - minimum) * share


def setup_hours(geometry: GeometryResult, config: PricingConfig) -> float:
    """FR-P4. One-time hours per order: CAM programming and fixturing."""
    faces = geometry.features.face_count
    programming = config.programming_base_hours + config.programming_hours_per_log2_face * (
        math.log2(faces) if faces > 0 else 0.0
    )
    fixturing = config.fixture_hours_per_setup * geometry.features.setups
    return programming + fixturing


def _money(value: float) -> float:
    return round(value, _MONEY_DECIMALS)


def _amount(value: float) -> float:
    return round(value, _QUANTITY_DECIMALS)


def price(
    geometry: GeometryResult, quantity: int, config: PricingConfig | None = None
) -> CostBreakdown:
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    config = config or PricingConfig()
    material = get_material(geometry.material)
    rate_per_hour = material.machining_hourly_rate_cents / 100
    rate_per_minute = rate_per_hour / 60

    # Material (FR-P1): priced on stock, not the finished part, with a minimum charge.
    computed_material = geometry.stock_mass_kg * material.price_per_kg
    # The minimum applies to the whole order: shops buy one bar for all the parts.
    computed_material_order = computed_material * quantity
    material_order = max(computed_material_order, config.min_material_charge)
    material_unit = material_order / quantity

    # Machine (FR-P2). Per-part time does not change with quantity.
    cycle = cycle_time(geometry, config)
    machine_unit = cycle.minutes * rate_per_minute

    # Setup (FR-P4): one-time programming and fixturing, shared across the parts. This is the
    # only quantity effect: the per-unit price falls as the order grows.
    setups = geometry.features.setups
    hours = setup_hours(geometry, config)
    setup_order = hours * rate_per_hour
    setup_unit = setup_order / quantity

    total_unit = material_unit + machine_unit + setup_unit

    return CostBreakdown(
        quantity=quantity,
        pricing_version=config.pricing_version,
        material=MaterialCost(
            stock_volume_cm3=_amount(geometry.stock_volume_cm3),
            part_volume_cm3=_amount(geometry.volume_cm3),
            removed_volume_cm3=_amount(max(0.0, geometry.stock_volume_cm3 - geometry.volume_cm3)),
            computed_cost_unit=_money(computed_material),
            computed_cost_order=_money(computed_material_order),
            minimum_charge=_money(config.min_material_charge),
            minimum_applied=computed_material_order < config.min_material_charge,
            cost_unit=_money(material_unit),
            cost_order=_money(material_order),
        ),
        machine=MachineCost(
            roughing_minutes=_amount(cycle.roughing_minutes),
            hole_minutes=_amount(cycle.hole_minutes),
            edge_minutes=_amount(cycle.edge_minutes),
            thin_wall_count=geometry.features.thin_wall_count,
            mrr_cm3_per_min=_amount(cycle.mrr_cm3_per_min),
            cycle_minutes=_amount(cycle.minutes),
            cost_unit=_money(machine_unit),
            cost_order=_money(machine_unit * quantity),
        ),
        setup=SetupCost(
            setups=setups,
            setup_hours=_amount(hours),
            cost_unit=_money(setup_unit),
            cost_order=_money(setup_order),
        ),
        total_cost_per_unit=_money(total_unit),
        total_order_cost=_money(total_unit * quantity),
    )
