"""
config.py
---------
Centralized configuration, loaded from environment variables.

No credentials or server details are ever hardcoded here. Copy
`.env.example` to `.env` and fill in your own values before running
the project.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from a local .env file, if present


class Config:
    # --- Remote server (SFTP) ---
    SFTP_HOST = os.getenv("SFTP_HOST", "test.rebex.net")   # public demo SFTP server
    SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
    SFTP_USERNAME = os.getenv("SFTP_USERNAME", "demo")
    SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "password")
    SFTP_REMOTE_DIR = os.getenv("SFTP_REMOTE_DIR", "/pub/example")

    # --- Local directories ---
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloaded_files")
    PROCESSED_DIR = os.getenv("PROCESSED_DIR", "processed_files")
    LOG_DIR = os.getenv("LOG_DIR", "logs")

    # --- Scheduling ---
    RUN_TIME = os.getenv("RUN_TIME", "19:00")  # 24h format, HH:MM
    RUN_ONCE_NOW = os.getenv("RUN_ONCE_NOW", "true").lower() == "true"

    # --- Notifications (optional) ---
    NOTIFY_ON_FAILURE = os.getenv("NOTIFY_ON_FAILURE", "false").lower() == "true"
    SMTP_SERVER = os.getenv("SMTP_SERVER", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
