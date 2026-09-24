"""
logger.py
---------
Sets up a daily rotating log file plus console output, so every run
leaves a clear audit trail of what was transferred, skipped, or failed.
"""

import logging
import os
from datetime import date
from src.config import Config


def get_logger(name: str = "file_sync") -> logging.Logger:
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(Config.LOG_DIR, f"log_{date.today()}.txt")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # avoid duplicate handlers on re-import
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
