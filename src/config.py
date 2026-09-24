"""
config.py
---------
Centralized configuration, loaded from environment variables.

No credentials or server details are hardcoded here. Copy `.env.example`
to `.env` and fill in your own values before running the project.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from a local .env file, if present


def _as_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- Remote server (SFTP) --- (no defaults: must come from .env)
    SFTP_HOST = os.getenv("SFTP_HOST", "")
    SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
    SFTP_USERNAME = os.getenv("SFTP_USERNAME", "")
    SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "")
    SFTP_REMOTE_DIR = os.getenv("SFTP_REMOTE_DIR", "")
    SFTP_TIMEOUT = int(os.getenv("SFTP_TIMEOUT", "30"))  # seconds

    # --- Host key verification ---
    # Strict mode refuses any server whose key is not in SFTP_KNOWN_HOSTS.
    # Populate it once with:  python -m src.trust_host
    SFTP_STRICT_HOST_KEY = _as_bool(os.getenv("SFTP_STRICT_HOST_KEY", "true"))
    SFTP_KNOWN_HOSTS = os.getenv("SFTP_KNOWN_HOSTS", "known_hosts")

    # --- Local directories ---
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloaded_files")
    PROCESSED_DIR = os.getenv("PROCESSED_DIR", "processed_files")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

    # --- Scheduling ---
    RUN_TIME = os.getenv("RUN_TIME", "19:00")  # 24h format, HH:MM
    RUN_ONCE_NOW = _as_bool(os.getenv("RUN_ONCE_NOW", "true"))

    # --- Notifications (optional) ---
    NOTIFY_ON_FAILURE = _as_bool(os.getenv("NOTIFY_ON_FAILURE", "false"))
    SMTP_SERVER = os.getenv("SMTP_SERVER", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")

    @classmethod
    def missing_settings(cls) -> list:
        """Names of required settings that are empty."""
        required = {
            "SFTP_HOST": cls.SFTP_HOST,
            "SFTP_USERNAME": cls.SFTP_USERNAME,
            "SFTP_PASSWORD": cls.SFTP_PASSWORD,
            "SFTP_REMOTE_DIR": cls.SFTP_REMOTE_DIR,
        }
        return [name for name, value in required.items() if not value]
