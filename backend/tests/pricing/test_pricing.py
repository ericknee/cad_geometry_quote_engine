from pathlib import Path

import pytest
from geometry.analyzer import analyze_file
from geometry.materials import DEFAULT_MATERIAL
from geometry.models import BoundingBox, Features, GeometryResult
from pricing import PricingConfig, lead_time, price
from pricing.cost import effective_mrr
from pydantic import ValidationError

GEAR = Path(__file__).resolve().parents[3] / "samples" / "vendra-gear.STEP"


def _geometry(
    *,
    stock=15.366,
    volume=1.9522,
    area=14.212,
    holes=1,
    setups=2,
    complexity=None,
    faces=99,
    edges=284,
    thin_walls=0,
) -> GeometryResult:
    return GeometryResult(
        file="part.step",
        material=DEFAULT_MATERIAL.name,
        bounding_box_mm=BoundingBox(length=23.0, width=22.0, height=12.0),
        stock_volume_cm3=stock,
        volume_cm3=volume,
        stock_mass_kg=DEFAULT_MATERIAL.mass_kg(stock),
        part_mass_kg=DEFAULT_MATERIAL.mass_kg(volume),
        surface_area_cm2=area,
        features=Features(
            face_count=faces,
            edge_count=edges,
            cylindrical_faces=0,
            holes_detected=holes,
            setups=setups,
            thin_wall_count=thin_walls,
            sa_to_volume_ratio=1.0,
            material_removal_ratio=0.5,
            complexity_score=complexity,
        ),
    )


def test_gear_quantity_one_by_hand():
    result = price(_geometry(), 1)
    # roughing = 13.4138 cm3 / 50 = 0.2683 min; edges = 284 x 0.05 = 14.2 min;
    # cycle = 0.2683 + 2 + 14.2 = 16.468 min -> $27.45
    # setup = (0.1 + 0.19 x log2(99)) + 2 x 0.1 = 1.560 h -> $155.96
    assert result.machine.cycle_minutes == pytest.approx(16.468, abs=1e-3)
    assert result.machine.cost_unit == pytest.approx(27.45, abs=0.01)
    assert result.setup.setup_hours == pytest.approx(1.560, abs=1e-3)
    assert result.setup.cost_unit == pytest.approx(155.96, abs=0.01)
    assert result.total_cost_per_unit == pytest.approx(193.40, abs=0.02)
    assert result.total_order_cost == result.total_cost_per_unit


def test_minimum_material_charge_applies_to_small_parts():
    material = price(_geometry(), 1).material
    assert material.minimum_applied
    assert material.computed_cost_unit < 1
    assert material.cost_unit == 10.0


def test_minimum_material_charge_is_per_order_not_per_unit():
    ten = price(_geometry(), 10).material
    # 10 parts use ~$2 of stock, so the $10 minimum is shared: $1 per part.
    assert ten.minimum_applied
    assert ten.cost_order == 10.0
    assert ten.cost_unit == 1.0
    # 100 parts use ~$21 of stock, above the minimum, so it no longer applies.
    hundred = price(_geometry(), 100).material
    assert not hundred.minimum_applied
    assert hundred.cost_order == pytest.approx(hundred.computed_cost_order)


def test_large_part_pays_computed_material_cost():
    # 1000 cm3 of stock x 2.7 g/cm3 = 2.7 kg x $5/kg = $13.50, above the $10 minimum.
    material = price(_geometry(stock=1000.0, volume=100.0), 1).material
    assert not material.minimum_applied
    assert material.cost_unit == 13.5


def test_only_setup_and_material_minimum_change_with_quantity():
    one, hundred = price(_geometry(), 1), price(_geometry(), 100)
    # Machine time and cost per part do not depend on quantity.
    assert hundred.machine.cycle_minutes == one.machine.cycle_minutes
    assert hundred.machine.cost_unit == one.machine.cost_unit
    expected = hundred.material.cost_unit + hundred.machine.cost_unit + hundred.setup.cost_unit
    assert hundred.total_cost_per_unit == pytest.approx(expected, abs=0.011)


def test_setup_is_shared_across_the_order():
    one, ten = price(_geometry(), 1), price(_geometry(), 10)
    assert ten.setup.cost_order == one.setup.cost_order
    assert ten.setup.cost_unit == pytest.approx(one.setup.cost_order / 10, abs=0.01)


def test_order_columns_match_unit_columns():
    # Unit values are rounded on their own, so the order value can differ by up to half a cent
    # per part (round-at-output, as the PRD requires).
    quantity = 10
    result = price(_geometry(), quantity)
    tolerance = 0.005 * quantity + 1e-9
    assert result.material.cost_order == pytest.approx(
        result.material.cost_unit * quantity, abs=tolerance
    )
    assert result.machine.cost_order == pytest.approx(
        result.machine.cost_unit * quantity, abs=tolerance
    )


def test_unit_price_falls_and_order_total_rises_as_quantity_rises():
    results = [price(_geometry(), q) for q in (1, 5, 10, 20, 21, 100, 101)]
    units = [r.total_cost_per_unit for r in results]
    orders = [r.total_order_cost for r in results]
    assert units == sorted(units, reverse=True)
    assert orders == sorted(orders)


def test_more_setups_cost_more():
    config = PricingConfig()
    one = price(_geometry(setups=1), 1).setup.setup_hours
    two = price(_geometry(setups=2), 1).setup.setup_hours
    assert two - one == pytest.approx(config.fixture_hours_per_setup, abs=1e-3)


def test_more_faces_cost_more_programming():
    assert (
        price(_geometry(faces=400), 1).setup.setup_hours
        > price(_geometry(faces=20), 1).setup.setup_hours
    )


def test_machine_rate_comes_from_the_material():
    # $100/h = 10,000 cents: 60 minutes of cycle cost exactly the material's hourly rate.
    assert DEFAULT_MATERIAL.machining_hourly_rate_cents == 10_000
    assert price(_geometry(), 1).material.computed_cost_unit == pytest.approx(
        15.366 * 2.7 / 1000 * 5.0, abs=0.01
    )


def test_complexity_score_does_not_change_the_price():
    plain = price(_geometry(), 1)
    harder = price(_geometry(complexity=2.0), 1)
    assert harder.machine.cycle_minutes == plain.machine.cycle_minutes
    assert harder.total_cost_per_unit == plain.total_cost_per_unit


def test_invalid_quantity():
    with pytest.raises(ValueError):
        price(_geometry(), 0)
    with pytest.raises(ValueError):
        lead_time(_geometry(), 0)


def test_gear_sample_is_inside_calibration_band():
    result = price(analyze_file(GEAR), 1)
    assert 190 <= result.total_cost_per_unit <= 195  # competitors charge ~$190-196


def test_lead_time_uses_full_cycle_hours():
    geometry = _geometry()
    result = lead_time(geometry, 100)
    cycle_hours = price(geometry, 1).machine.cycle_minutes / 60
    assert result.total_machine_hours == pytest.approx(1.560 + cycle_hours * 100, abs=0.01)
    assert result.work_days == 4
    assert result.days == 5 + 4 + 0


def test_lead_time_small_order_is_minimum_plus_one_day():
    result = lead_time(_geometry(), 1)
    assert (result.work_days, result.days) == (1, 6)


def test_lead_time_exact_day_boundary_does_not_round_up():
    # 8.0 productive hours exactly: all setup parts zero except 8 h of programming base time.
    config = PricingConfig(
        fixture_hours_per_setup=0.0,
        programming_base_hours=8.0,
        programming_hours_per_log2_face=0.0,
        minutes_per_hole=0.0,
        minutes_per_edge=0.0,
    )
    geometry = _geometry(stock=1.0, volume=1.0, area=1e-9, holes=0, setups=1)
    assert lead_time(geometry, 1, config).work_days == 1


def test_config_rejects_bad_tables():
    with pytest.raises(ValidationError):
        PricingConfig(complexity_buffer_bands=((1.5, 0),))


def test_thin_walls_lower_the_mrr_from_50_to_20_over_0_to_8_walls():
    config = PricingConfig()
    assert effective_mrr(0, config) == 50.0  # no thin walls, no change
    assert effective_mrr(4, config) == pytest.approx(35.0)
    assert effective_mrr(8, config) == 20.0
    assert effective_mrr(20, config) == 20.0  # capped


def test_thin_walls_slow_roughing_only():
    plain, thin = (
        price(_geometry(thin_walls=0), 1).machine,
        price(_geometry(thin_walls=8), 1).machine,
    )
    assert thin.roughing_minutes == pytest.approx(plain.roughing_minutes * 50 / 20, abs=0.01)
    assert thin.hole_minutes == plain.hole_minutes


def test_minimum_mrr_must_not_exceed_the_base_rate():
    with pytest.raises(ValidationError):
        PricingConfig(min_roughing_cm3_per_min=500.0)


def test_gear_quote_is_inside_the_calibration_target():
    assert 190 <= price(analyze_file(GEAR), 1).total_cost_per_unit <= 195
