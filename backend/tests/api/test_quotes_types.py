from datetime import UTC, datetime

import pytest
from api.types.quotes_types import QuoteDetail, QuoteStatus, QuoteSummary, StatusUpdate
from geometry.analyzer import analyze_file
from pricing import lead_time, price
from pydantic import ValidationError

NOW = datetime(2026, 11, 4, tzinfo=UTC)


def _queued() -> QuoteDetail:
    return QuoteDetail(
        id="abc",
        file_name="gear.step",
        file_hash="h",
        quantity=10,
        material="6061 Aluminum",
        status=QuoteStatus.QUEUED,
        created_at=NOW,
        updated_at=NOW,
    )


def test_queued_quote_has_no_results_yet():
    quote = _queued()
    assert quote.geometry is None
    assert quote.cost_breakdown is None
    assert quote.lead_time_days is None
    assert QuoteSummary.from_document(quote.model_dump()).total_cost_per_unit is None


def test_summary_takes_prices_from_the_breakdown():
    geometry = analyze_file("samples/vendra-gear.STEP")
    cost, lead = price(geometry, 10), lead_time(geometry, 10)
    quote = _queued().model_copy(
        update={
            "status": QuoteStatus.QUOTED,
            "geometry": geometry,
            "cost_breakdown": cost,
            "lead_time": lead,
            "lead_time_days": lead.days,
        }
    )
    summary = QuoteSummary.from_document(quote.model_dump())
    assert summary.total_cost_per_unit == cost.total_cost_per_unit
    assert summary.total_order_cost == cost.total_order_cost
    assert summary.lead_time_days == lead.days


def test_status_update_rejects_unknown_status():
    assert StatusUpdate(status="reviewed").status is QuoteStatus.REVIEWED
    with pytest.raises(ValidationError):
        StatusUpdate(status="banana")
