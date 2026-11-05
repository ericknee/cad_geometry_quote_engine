import asyncio

import pytest
from api import worker


class FlakyService:
    """process_next_job plays back outcomes: an Exception is raised, True/False is returned."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)

    async def recover_stale_jobs(self):
        return 0, 0

    async def process_next_job(self):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    recorded: list[float] = []

    async def fake_sleep(seconds):
        recorded.append(seconds)

    monkeypatch.setattr(worker.asyncio, "sleep", fake_sleep)
    return recorded


async def test_backs_off_exponentially_then_exits_after_three_retries(sleeps):
    service = FlakyService(*[RuntimeError("db down")] * 4)
    with pytest.raises(RuntimeError, match="db down"):
        await worker.run(service, poll_seconds=1.0)
    assert sleeps == [5.0, 10.0, 20.0]


async def test_success_resets_the_failure_count(sleeps):
    err = RuntimeError("blip")
    service = FlakyService(err, err, True, err, err, True, asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await worker.run(service, poll_seconds=1.0)
    assert sleeps == [5.0, 10.0, 5.0, 10.0]
