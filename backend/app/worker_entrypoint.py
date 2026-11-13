from __future__ import annotations

import asyncio
import logging
import signal

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.auth.email_delivery import FileEmailDelivery, SmtpEmailDelivery
from app.data_ingestion.types import ScrapeJob
from app.db.session import get_session_factory
from app.workers.background_jobs import DurableJobStore, BackgroundWorker, EmailOutboxStore, EmailOutboxWorker
from app.workers.bootstrap import build_product_intelligence_runtime


async def main() -> None:
    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_logs=settings.log_json)
    runtime = build_product_intelligence_runtime(settings)
    session_factory = get_session_factory(settings)
    store = DurableJobStore(session_factory, settings)
    worker = BackgroundWorker(
        store,
        {"scrape_ingestion": lambda payload: runtime.execute(ScrapeJob.model_validate(payload))},
        settings,
    )
    delivery = FileEmailDelivery(settings) if settings.email_delivery_mode == "file" else SmtpEmailDelivery(settings)
    email_worker = EmailOutboxWorker(EmailOutboxStore(session_factory, settings), delivery, settings)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, worker.stop)
        loop.add_signal_handler(sig, email_worker.stop)
    logging.getLogger(__name__).info("background worker started")
    await asyncio.gather(worker.run_forever(), email_worker.run_forever())


if __name__ == "__main__":
    asyncio.run(main())
