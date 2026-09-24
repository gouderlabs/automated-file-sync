"""
main.py
-------
Entry point. Runs the sync once immediately (if RUN_ONCE_NOW=true),
then schedules it to run daily at RUN_TIME, indefinitely.
"""

import time
import schedule

from src.config import Config
from src.logger import get_logger
from src.transfer import run_sync
from src.notifier import notify_failure

logger = get_logger()


def job():
    try:
        summary = run_sync()
        logger.info(
            f"Sync summary — downloaded: {len(summary['downloaded'])}, "
            f"skipped: {len(summary['skipped'])}, errors: {len(summary['errors'])}"
        )
        if summary["errors"]:
            notify_failure(f"Some files failed to transfer: {summary['errors']}")
    except Exception as e:
        logger.error(f"Sync job crashed: {e}")
        notify_failure(str(e))


if __name__ == "__main__":
    if Config.RUN_ONCE_NOW:
        logger.info("Running an immediate sync before starting the schedule...")
        job()

    schedule.every().day.at(Config.RUN_TIME).do(job)
    logger.info(f"Scheduler started. Job will run daily at {Config.RUN_TIME}.")

    while True:
        schedule.run_pending()
        time.sleep(30)
