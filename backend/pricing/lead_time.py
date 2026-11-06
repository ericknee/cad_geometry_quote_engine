"""Lead time in business days (PRD 7.3)."""

import math

from geometry.models import GeometryResult

from pricing.config import PricingConfig
from pricing.cost import cycle_time, setup_hours
from pricing.models import LeadTime

_HOURS_DECIMALS = 3
_FLOAT_NOISE_DECIMALS = 9  # stops 8.0000000001 hours from rounding up to a whole extra day


def complexity_buffer_days(face_count: int, machine_days: float, config: PricingConfig) -> int:
    """Whole days: a share of machine days that grows with face count, up to the max rate."""
    complexity = min(face_count / config.buffer_full_faces, 1)
    buffer = machine_days * config.max_buffer_rate * complexity
    return math.ceil(round(buffer, _FLOAT_NOISE_DECIMALS))


def lead_time(
    geometry: GeometryResult, quantity: int, config: PricingConfig | None = None
) -> LeadTime:
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    config = config or PricingConfig()

    cycle = cycle_time(geometry, config)
    setup = setup_hours(geometry, config)
    total_hours = setup + cycle.minutes / 60 * quantity

    machine_days = total_hours / config.productive_hours_per_day
    work_days = math.ceil(round(machine_days, _FLOAT_NOISE_DECIMALS))
    # Each part is rounded up on its own, so the breakdown shows whole days only.
    buffer_days = complexity_buffer_days(geometry.features.face_count, machine_days, config)
    return LeadTime(
        total_machine_hours=round(total_hours, _HOURS_DECIMALS),
        productive_hours_per_day=config.productive_hours_per_day,
        work_days=work_days,
        complexity_buffer_days=buffer_days,
        min_lead_time_days=config.min_lead_time_days,
        days=config.min_lead_time_days + work_days + buffer_days,
    )
