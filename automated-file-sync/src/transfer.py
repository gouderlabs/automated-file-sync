"""
transfer.py
-----------
Core logic: connect to a remote SFTP server, download any files that
haven't been processed yet, move them into a "processed" folder, and
log every step. This is the reusable engine behind the daily job.
"""

import os
import shutil
import paramiko
from src.config import Config
from src.logger import get_logger

logger = get_logger()


def connect() -> paramiko.SFTPClient:
    transport = paramiko.Transport((Config.SFTP_HOST, Config.SFTP_PORT))
    transport.connect(username=Config.SFTP_USERNAME, password=Config.SFTP_PASSWORD)
    return paramiko.SFTPClient.from_transport(transport)


def list_remote_files(sftp: paramiko.SFTPClient) -> list[str]:
    try:
        return sftp.listdir(Config.SFTP_REMOTE_DIR)
    except FileNotFoundError:
        logger.error(f"Remote directory not found: {Config.SFTP_REMOTE_DIR}")
        return []


def already_downloaded(filename: str) -> bool:
    return os.path.exists(os.path.join(Config.PROCESSED_DIR, filename))


def download_file(sftp: paramiko.SFTPClient, filename: str) -> str:
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    remote_path = f"{Config.SFTP_REMOTE_DIR}/{filename}"
    local_path = os.path.join(Config.DOWNLOAD_DIR, filename)
    sftp.get(remote_path, local_path)
    return local_path


def move_to_processed(local_path: str, filename: str) -> None:
    os.makedirs(Config.PROCESSED_DIR, exist_ok=True)
    shutil.move(local_path, os.path.join(Config.PROCESSED_DIR, filename))


def run_sync() -> dict:
    """
    Runs one full sync pass. Returns a summary dict so the caller
    (scheduler or CLI) can report on what happened.
    """
    summary = {"downloaded": [], "skipped": [], "errors": []}

    logger.info(f"Connecting to {Config.SFTP_HOST}:{Config.SFTP_PORT} ...")
    sftp = connect()

    try:
        files = list_remote_files(sftp)
        logger.info(f"Found {len(files)} file(s) on remote server.")

        for filename in files:
            if already_downloaded(filename):
                logger.info(f"Skipping already processed file: {filename}")
                summary["skipped"].append(filename)
                continue

            try:
                local_path = download_file(sftp, filename)
                move_to_processed(local_path, filename)
                logger.info(f"Transferred: {filename}")
                summary["downloaded"].append(filename)
            except Exception as e:
                logger.error(f"Failed to transfer {filename}: {e}")
                summary["errors"].append(filename)

    finally:
        sftp.close()
        logger.info("Connection closed.")

    return summary
