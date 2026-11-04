"""Lead time in business days (PRD 7.3). Uses undiscounted hours: discounts never shorten it."""

import math

from geometry.models import GeometryResult

from pricing.config import PricingConfig
from pricing.cost import cycle_time, setup_hours
from pricing.models import LeadTime

_HOURS_DECIMALS = 3
_FLOAT_NOISE_DECIMALS = 9  # stops 8.0000000001 hours from rounding up to a whole extra day


def complexity_buffer_days(score: float, config: PricingConfig) -> int:
    """Extra days for the highest band whose minimum score is not above `score`."""
    days = 0
    for minimum, band_days in config.complexity_buffer_bands:
        if score >= minimum:
            days = band_days
    return days


def lead_time(
    geometry: GeometryResult, quantity: int, config: PricingConfig | None = None
) -> LeadTime:
    if quantity < 1:
        raise ValueError("quantity must be at least 1")
    config = config or PricingConfig()

    cycle = cycle_time(geometry, config)
    setup = setup_hours(geometry.features.setups, config)
    total_hours = setup + cycle.minutes / 60 * quantity

    work_days = math.ceil(
        round(total_hours / config.productive_hours_per_day, _FLOAT_NOISE_DECIMALS)
    )
    buffer_days = complexity_buffer_days(cycle.complexity_score, config)
    return LeadTime(
        total_machine_hours=round(total_hours, _HOURS_DECIMALS),
        productive_hours_per_day=config.productive_hours_per_day,
        work_days=work_days,
        complexity_buffer_days=buffer_days,
        min_lead_time_days=config.min_lead_time_days,
        days=config.min_lead_time_days + work_days + buffer_days,
    )
