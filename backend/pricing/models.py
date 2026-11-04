"""Result types (FR-P6). Money in dollars, rounded to cents here and nowhere earlier."""

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class MaterialCost(_Frozen):
    stock_volume_cm3: float
    part_volume_cm3: float
    removed_volume_cm3: float  # stock - part
    computed_cost_unit: float  # stock x density x price, before the minimum
    minimum_charge: float
    minimum_applied: bool
    cost_unit: float  # max(computed, minimum)
    cost_order: float


class MachineCost(_Frozen):
    """Machine time and cost before any quantity discount."""

    roughing_minutes: float
    finishing_minutes: float
    hole_minutes: float
    handling_minutes: float
    complexity_score: float  # the value actually used
    cycle_minutes: float  # (sum of the four) x complexity
    cost_unit: float
    cost_order: float


class SetupCost(_Frozen):
    setups: int
    setup_hours: float
    cost_unit: float  # shared by the whole order, so it falls as quantity grows
    cost_order: float


class QuantityDiscount(_Frozen):
    rate: float
    amount_unit: float  # machine cost x rate
    amount_order: float


class CostBreakdown(_Frozen):
    quantity: int
    pricing_version: str
    material: MaterialCost
    machine: MachineCost
    setup: SetupCost
    discount: QuantityDiscount
    total_cost_per_unit: float
    total_order_cost: float


class LeadTime(_Frozen):
    total_machine_hours: float  # setup hours + undiscounted cycle hours x quantity
    productive_hours_per_day: float
    work_days: int
    complexity_buffer_days: int
    min_lead_time_days: int
    days: int  # business days, stored as the quote's lead_time_days
