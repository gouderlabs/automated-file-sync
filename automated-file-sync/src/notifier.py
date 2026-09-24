"""
notifier.py
-----------
Optional email alert sent when a transfer run fails, so a human finds
out immediately instead of discovering a silent failure days later.
Disabled by default (see NOTIFY_ON_FAILURE in config).
"""

import smtplib
from email.mime.text import MIMEText
from src.config import Config
from src.logger import get_logger

logger = get_logger()


def notify_failure(error_message: str) -> None:
    if not Config.NOTIFY_ON_FAILURE:
        return

    if not (Config.SMTP_SERVER and Config.SMTP_USERNAME and Config.ALERT_EMAIL_TO):
        logger.warning("NOTIFY_ON_FAILURE is enabled but SMTP settings are incomplete.")
        return

    msg = MIMEText(f"The automated file sync job failed:\n\n{error_message}")
    msg["Subject"] = "[ALERT] File Sync Job Failed"
    msg["From"] = Config.SMTP_USERNAME
    msg["To"] = Config.ALERT_EMAIL_TO

    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_USERNAME, [Config.ALERT_EMAIL_TO], msg.as_string())
        logger.info("Failure notification email sent.")
    except Exception as e:
        logger.error(f"Could not send failure notification: {e}")
