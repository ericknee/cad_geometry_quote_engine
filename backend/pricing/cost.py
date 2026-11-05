"""price(): geometry + quantity -> cost breakdown (FR-P1..P6). Pure: no I/O, no globals.

Everything is computed unrounded; money and intermediates are rounded only when the result
models are built, so rounding never feeds into another calculation.
"""

from dataclasses import dataclass

from geometry.models import GeometryResult

from pricing.config import PricingConfig
from pricing.models import (
    CostBreakdown,
    MachineCost,
    MaterialCost,
    QuantityDiscount,
    SetupCost,
)

_MONEY_DECIMALS = 2
_QUANTITY_DECIMALS = 3  # minutes, hours, volumes


@dataclass(frozen=True)
class Cycle:
    """Unrounded machine time for one part, before any discount."""

    roughing_minutes: float
    finishing_minutes: float
    hole_minutes: float
    handling_minutes: float
    complexity_score: float

    @property
    def minutes(self) -> float:
        base = (
            self.roughing_minutes
            + self.finishing_minutes
            + self.hole_minutes
            + self.handling_minutes
        )
        return base * self.complexity_score


def cycle_time(geometry: GeometryResult, config: PricingConfig) -> Cycle:
    """FR-P2. Shared with the lead-time model."""
    features = geometry.features
    removed = max(0.0, geometry.stock_volume_cm3 - geometry.volume_cm3)
    score = features.complexity_score
    return Cycle(
        roughing_minutes=removed / config.roughing_cm3_per_min,
        finishing_minutes=geometry.surface_area_cm2 / config.finishing_cm2_per_min,
        hole_minutes=features.holes_detected * config.minutes_per_hole,
        handling_minutes=config.handling_minutes,
        complexity_score=config.default_complexity_score if score is None else score,
    )


def setup_hours(setups: int, config: PricingConfig) -> float:
    """FR-P4. Each setup after the first adds a fixed share of the base time."""
    return config.base_setup_hours * (1 + config.setup_extra_per_setup * (setups - 1))


def discount_rate(quantity: int, config: PricingConfig) -> float:
    """FR-P3. The tier with the largest minimum quantity not above `quantity`."""
    rate = 0.0
    for minimum, tier_rate in config.discount_tiers:
        if quantity >= minimum:
            rate = tier_rate
    return rate


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
    rate_per_minute = config.machine_rate_per_hour / 60

    # Material (FR-P1): priced on stock, not the finished part, with a minimum charge.
    computed_material = (
        geometry.stock_volume_cm3 * config.density_g_per_cm3 / 1000 * config.material_price_per_kg
    )
    material_unit = max(computed_material, config.min_material_charge)

    # Machine (FR-P2). Never reduced by the quantity discount.
    cycle = cycle_time(geometry, config)
    machine_unit = cycle.minutes * rate_per_minute

    # Setup (FR-P4): one cost for the whole order, shared across the parts.
    setups = geometry.features.setups
    setup_order = setup_hours(setups, config) * config.machine_rate_per_hour
    setup_unit = setup_order / quantity

    # Discount (FR-P3/P5): taken off the machine cost, shown as its own line.
    rate = discount_rate(quantity, config)
    discount_unit = machine_unit * rate

    total_unit = material_unit + machine_unit + setup_unit - discount_unit

    return CostBreakdown(
        quantity=quantity,
        pricing_version=config.pricing_version,
        material=MaterialCost(
            stock_volume_cm3=_amount(geometry.stock_volume_cm3),
            part_volume_cm3=_amount(geometry.volume_cm3),
            removed_volume_cm3=_amount(max(0.0, geometry.stock_volume_cm3 - geometry.volume_cm3)),
            computed_cost_unit=_money(computed_material),
            minimum_charge=_money(config.min_material_charge),
            minimum_applied=computed_material < config.min_material_charge,
            cost_unit=_money(material_unit),
            cost_order=_money(material_unit * quantity),
        ),
        machine=MachineCost(
            roughing_minutes=_amount(cycle.roughing_minutes),
            finishing_minutes=_amount(cycle.finishing_minutes),
            hole_minutes=_amount(cycle.hole_minutes),
            handling_minutes=_amount(cycle.handling_minutes),
            complexity_score=cycle.complexity_score,
            cycle_minutes=_amount(cycle.minutes),
            cost_unit=_money(machine_unit),
            cost_order=_money(machine_unit * quantity),
        ),
        setup=SetupCost(
            setups=setups,
            setup_hours=_amount(setup_hours(setups, config)),
            cost_unit=_money(setup_unit),
            cost_order=_money(setup_order),
        ),
        discount=QuantityDiscount(
            rate=rate,
            amount_unit=_money(discount_unit),
            amount_order=_money(discount_unit * quantity),
        ),
        total_cost_per_unit=_money(total_unit),
        total_order_cost=_money(total_unit * quantity),
    )
