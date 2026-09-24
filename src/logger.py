"""
logger.py
---------
Sets up a daily-rotating log file plus console output, so every run
leaves a clear audit trail of what was transferred, skipped, or failed.

The active file is `file_sync.log`. At midnight it is renamed to
`file_sync.log.YYYY-MM-DD` and a new one starts, even if the process
keeps running for weeks. Files older than LOG_RETENTION_DAYS are deleted.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler

from src.config import Config


def get_logger(name: str = "file_sync") -> logging.Logger:
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # avoid duplicate handlers on re-import
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = TimedRotatingFileHandler(
            os.path.join(Config.LOG_DIR, "file_sync.log"),
            when="midnight",
            backupCount=Config.LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
