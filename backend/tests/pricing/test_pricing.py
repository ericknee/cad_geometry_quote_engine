from pathlib import Path

import pytest
from geometry.analyzer import analyze_file
from geometry.models import BoundingBox, Features, GeometryResult
from pricing import PricingConfig, lead_time, price
from pricing.cost import discount_rate
from pydantic import ValidationError

GEAR = Path(__file__).resolve().parents[3] / "samples" / "vendra-gear.STEP"


def _geometry(
    *, stock=15.366, volume=1.9522, area=14.212, holes=1, setups=2, complexity=None
) -> GeometryResult:
    return GeometryResult(
        file="part.step",
        bounding_box_mm=BoundingBox(length=23.0, width=22.0, height=12.0),
        stock_volume_cm3=stock,
        volume_cm3=volume,
        surface_area_cm2=area,
        features=Features(
            face_count=1,
            edge_count=1,
            cylindrical_faces=0,
            holes_detected=holes,
            setups=setups,
            sa_to_volume_ratio=1.0,
            material_removal_ratio=0.5,
            complexity_score=complexity,
        ),
    )


def test_gear_quantity_one_by_hand():
    result = price(_geometry(), 1)
    # cycle = 13.4138 + 14.212 + 2 + 3 = 32.6258 min -> $54.38; setup = 1.12 x 1.25 h -> $140
    assert result.machine.cycle_minutes == pytest.approx(32.626, abs=1e-3)
    assert result.machine.cost_unit == pytest.approx(54.38, abs=0.01)
    assert result.setup.setup_hours == pytest.approx(1.4)
    assert result.setup.cost_unit == 140.0
    assert result.total_cost_per_unit == pytest.approx(204.38, abs=0.01)
    assert result.total_order_cost == result.total_cost_per_unit


def test_minimum_material_charge_applies_to_small_parts():
    material = price(_geometry(), 1).material
    assert material.minimum_applied
    assert material.computed_cost_unit < 1
    assert material.cost_unit == 10.0


def test_large_part_pays_computed_material_cost():
    # 1000 cm3 of stock x 2.7 g/cm3 = 2.7 kg x $5/kg = $13.50, above the $10 minimum.
    material = price(_geometry(stock=1000.0, volume=100.0), 1).material
    assert not material.minimum_applied
    assert material.cost_unit == 13.5


@pytest.mark.parametrize(
    ("quantity", "rate"),
    [
        (1, 0.0),
        (5, 0.0),
        (6, 0.10),
        (20, 0.10),
        (21, 0.20),
        (100, 0.20),
        (101, 0.30),
        (10000, 0.30),
    ],
)
def test_discount_tiers(quantity, rate):
    assert discount_rate(quantity, PricingConfig()) == rate


def test_discount_applies_to_totals_only():
    one, hundred = price(_geometry(), 1), price(_geometry(), 100)
    # Machine time and cost per part are never reduced; the discount is its own line.
    assert hundred.machine.cycle_minutes == one.machine.cycle_minutes
    assert hundred.machine.cost_unit == one.machine.cost_unit
    assert hundred.discount.rate == 0.20
    assert hundred.discount.amount_unit == pytest.approx(one.machine.cost_unit * 0.20, abs=0.01)
    expected = (
        hundred.material.cost_unit
        + hundred.machine.cost_unit
        + hundred.setup.cost_unit
        - hundred.discount.amount_unit
    )
    assert hundred.total_cost_per_unit == pytest.approx(expected, abs=0.011)


def test_setup_is_shared_across_the_order():
    one, ten = price(_geometry(), 1), price(_geometry(), 10)
    assert ten.setup.cost_order == one.setup.cost_order == 140.0
    assert ten.setup.cost_unit == pytest.approx(14.0)


def test_order_columns_match_unit_columns():
    # Unit values are rounded on their own, so the order value can differ by up to half a cent
    # per part (round-at-output, as the PRD requires).
    quantity = 10
    result = price(_geometry(), quantity)
    tolerance = 0.005 * quantity + 1e-9
    assert result.material.cost_order == result.material.cost_unit * quantity
    assert result.machine.cost_order == pytest.approx(
        result.machine.cost_unit * quantity, abs=tolerance
    )
    assert result.discount.amount_order == pytest.approx(
        result.discount.amount_unit * quantity, abs=tolerance
    )


def test_unit_price_falls_as_quantity_rises():
    prices = [price(_geometry(), q).total_cost_per_unit for q in (1, 10, 100)]
    assert prices[0] > prices[1] > prices[2]


def test_more_setups_cost_more():
    assert (
        price(_geometry(setups=4), 1).setup.setup_hours
        > price(_geometry(setups=2), 1).setup.setup_hours
    )
    assert price(_geometry(setups=1), 1).setup.setup_hours == pytest.approx(1.12)


def test_complexity_score_scales_cycle_time_and_falls_back():
    plain = price(_geometry(), 1).machine
    harder = price(_geometry(complexity=2.0), 1).machine
    assert plain.complexity_score == 1.0
    assert harder.cycle_minutes == pytest.approx(plain.cycle_minutes * 2, abs=1e-3)


def test_invalid_quantity():
    with pytest.raises(ValueError):
        price(_geometry(), 0)
    with pytest.raises(ValueError):
        lead_time(_geometry(), 0)


def test_gear_sample_is_inside_calibration_band():
    result = price(analyze_file(GEAR), 1)
    assert 150 <= result.total_cost_per_unit <= 240  # PRD target; competitors charge ~$190-196


def test_lead_time_uses_undiscounted_hours():
    geometry = _geometry()
    result = lead_time(geometry, 100)
    cycle_hours = price(geometry, 1).machine.cycle_minutes / 60
    assert result.total_machine_hours == pytest.approx(1.4 + cycle_hours * 100, abs=0.01)
    assert result.work_days == 7
    assert result.days == 5 + 7 + 0


def test_lead_time_small_order_is_minimum_plus_one_day():
    result = lead_time(_geometry(), 1)
    assert (result.work_days, result.days) == (1, 6)


def test_lead_time_exact_day_boundary_does_not_round_up():
    # 8.0 productive hours exactly: setup 1.12 h at 1 setup + cycle chosen to total 8 h.
    config = PricingConfig(base_setup_hours=8.0, handling_minutes=0.0, minutes_per_hole=0.0)
    geometry = _geometry(stock=1.0, volume=1.0, area=1e-9, holes=0, setups=1)
    assert lead_time(geometry, 1, config).work_days == 1


def test_config_rejects_bad_tables():
    with pytest.raises(ValidationError):
        PricingConfig(discount_tiers=((2, 0.0),))
    with pytest.raises(ValidationError):
        PricingConfig(discount_tiers=((1, 0.0), (1, 0.1)))
    with pytest.raises(ValidationError):
        PricingConfig(discount_tiers=((1, 1.5),))
    with pytest.raises(ValidationError):
        PricingConfig(complexity_buffer_bands=((1.5, 0),))
