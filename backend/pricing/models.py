"""Result types (FR-P6). Money in dollars, rounded to cents here and nowhere earlier."""

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class MaterialCost(_Frozen):
    stock_volume_cm3: float
    part_volume_cm3: float
    removed_volume_cm3: float  # stock - part
    computed_cost_unit: float  # stock mass x price, before the minimum
    computed_cost_order: float  # computed_cost_unit x quantity
    minimum_charge: float  # per order
    minimum_applied: bool
    cost_order: float  # max(computed order cost, minimum)
    cost_unit: float  # cost_order / quantity


class MachineCost(_Frozen):
    """Machine time and cost for one part."""

    roughing_minutes: float
    hole_minutes: float
    edge_minutes: float
    thin_wall_count: int
    mrr_cm3_per_min: float  # roughing rate used, after the thin-wall cut
    cycle_minutes: float  # roughing + holes + edges
    cost_unit: float
    cost_order: float


class SetupCost(_Frozen):
    setups: int
    setup_hours: float
    cost_unit: float  # shared by the whole order, so it falls as quantity grows
    cost_order: float


class CostBreakdown(_Frozen):
    quantity: int
    pricing_version: str
    material: MaterialCost
    machine: MachineCost
    setup: SetupCost
    total_cost_per_unit: float
    total_order_cost: float


class LeadTime(_Frozen):
    total_machine_hours: float  # setup hours + cycle hours x quantity
    productive_hours_per_day: float
    work_days: int
    complexity_buffer_days: int
    min_lead_time_days: int
    days: int  # business days, stored as the quote's lead_time_days
