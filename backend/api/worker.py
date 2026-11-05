"""Background worker: `python -m api.worker`. Takes queued quotes one at a time and finishes them.

Run any number of workers; the atomic claim in the repository keeps them from sharing a job.
"""

import asyncio
import logging
import time

from api.config import Settings
from api.db.database import create_client, get_database
from api.db.indexes import ensure_indexes
from api.repositories.quotes_repository import QuotesRepository
from api.services.quotes_service import QuotesService

logger = logging.getLogger("api.worker")

RECOVERY_INTERVAL_SECONDS = 60.0
ERROR_BACKOFF_SECONDS = 5.0  # doubles per consecutive failure: 5, 10, 20
MAX_LOOP_RETRIES = 3


async def run(service: QuotesService, poll_seconds: float) -> None:
    """Process jobs forever; sleep only when the queue is empty.

    An error in one iteration (e.g. MongoDB briefly unreachable) is logged and retried with
    exponential backoff. After MAX_LOOP_RETRIES consecutive failures the error is re-raised so the
    process exits (Docker restarts it). A job left in `processing` is picked up by stale-job
    recovery.
    """
    last_recovery = float("-inf")
    failures = 0
    while True:
        try:
            # Also on every start, so jobs left behind by a crashed worker are picked up.
            if time.monotonic() - last_recovery >= RECOVERY_INTERVAL_SECONDS:
                requeued, failed = await service.recover_stale_jobs()
                last_recovery = time.monotonic()  # only after success, so a failure retries soon
                if requeued or failed:
                    logger.warning("Recovered stale jobs: %d requeued, %d failed", requeued, failed)
            if not await service.process_next_job():
                await asyncio.sleep(poll_seconds)
            failures = 0
        except Exception:  # CancelledError is not an Exception, so shutdown still works.
            failures += 1
            if failures > MAX_LOOP_RETRIES:
                logger.exception("Worker failed %d times in a row; exiting", failures)
                raise
            delay = ERROR_BACKOFF_SECONDS * 2 ** (failures - 1)
            logger.exception(
                "Worker iteration failed; retry %d/%d in %g s", failures, MAX_LOOP_RETRIES, delay
            )
            await asyncio.sleep(delay)


async def main() -> None:
    settings = Settings()
    client = create_client(settings)
    try:
        db = get_database(client, settings)
        await ensure_indexes(db)
        service = QuotesService(QuotesRepository(db), settings)
        logger.info("Worker started")
        await run(service, settings.worker_poll_seconds)
    finally:
        await client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
