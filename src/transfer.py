"""
transfer.py
-----------
Core logic: connect to a remote SFTP server, download every file that is
new or has changed since the last run, move it into a "processed" folder,
and log every step.

Change detection is stateless: after a download, the local file's
modification time is set to the remote one. On the next run, a file is
considered unchanged only if its size AND modification time match.
"""

import os
import posixpath
import shutil
import stat
from contextlib import contextmanager
from typing import Iterator, List

import paramiko

from src.config import Config
from src.logger import get_logger

logger = get_logger()

# SFTP servers and some filesystems (e.g. FAT) don't keep sub-second or
# even odd-second precision, so tiny timestamp differences are ignored.
MTIME_TOLERANCE_SECONDS = 2


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------
def build_client() -> paramiko.SSHClient:
    """SSH client configured with the host key policy from the settings."""
    client = paramiko.SSHClient()

    if Config.SFTP_STRICT_HOST_KEY:
        if os.path.exists(Config.SFTP_KNOWN_HOSTS):
            client.load_host_keys(Config.SFTP_KNOWN_HOSTS)
        # Any server whose key isn't already trusted is refused.
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        logger.warning(
            "Host key verification is DISABLED (SFTP_STRICT_HOST_KEY=false). "
            "Use this for quick tests only."
        )
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    return client


@contextmanager
def sftp_session() -> Iterator[paramiko.SFTPClient]:
    """Open an SFTP session and always close everything, even on error."""
    client = build_client()
    try:
        try:
            client.connect(
                hostname=Config.SFTP_HOST,
                port=Config.SFTP_PORT,
                username=Config.SFTP_USERNAME,
                password=Config.SFTP_PASSWORD,
                timeout=Config.SFTP_TIMEOUT,
                look_for_keys=False,
                allow_agent=False,
            )
        except paramiko.BadHostKeyException:
            logger.error(
                f"HOST KEY MISMATCH for {Config.SFTP_HOST}: the server key differs "
                f"from the one in {Config.SFTP_KNOWN_HOSTS}. Refusing to connect "
                "(possible man-in-the-middle attack, or the server was reinstalled)."
            )
            raise
        except paramiko.SSHException as e:
            if Config.SFTP_STRICT_HOST_KEY and "known_hosts" in str(e):
                logger.error(
                    f"Unknown host key for {Config.SFTP_HOST}. "
                    "Verify it and trust it once with:  python -m src.trust_host"
                )
            raise

        sftp = client.open_sftp()
        try:
            yield sftp
        finally:
            sftp.close()
    finally:
        client.close()
        logger.info("Connection closed.")


# --------------------------------------------------------------------------
# Listing and change detection
# --------------------------------------------------------------------------
def is_directory(attr: paramiko.SFTPAttributes) -> bool:
    return attr.st_mode is not None and stat.S_ISDIR(attr.st_mode)


def list_remote_files(sftp: paramiko.SFTPClient) -> List[paramiko.SFTPAttributes]:
    """Regular remote entries (directories are skipped) with size and mtime."""
    try:
        entries = sftp.listdir_attr(Config.SFTP_REMOTE_DIR)
    except FileNotFoundError:
        logger.error(f"Remote directory not found: {Config.SFTP_REMOTE_DIR}")
        raise  # fail loud: the caller logs it and sends the alert
    return [e for e in entries if not is_directory(e)]


def classify(attr: paramiko.SFTPAttributes) -> str:
    """Return 'new', 'changed' or 'unchanged' for a remote file."""
    local_path = os.path.join(Config.PROCESSED_DIR, attr.filename)
    if not os.path.exists(local_path):
        return "new"

    local = os.stat(local_path)
    if attr.st_size is not None and local.st_size != attr.st_size:
        return "changed"
    if (
        attr.st_mtime is not None
        and abs(int(local.st_mtime) - int(attr.st_mtime)) > MTIME_TOLERANCE_SECONDS
    ):
        return "changed"
    return "unchanged"


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------
def download_file(sftp: paramiko.SFTPClient, attr: paramiko.SFTPAttributes) -> str:
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    remote_path = posixpath.join(Config.SFTP_REMOTE_DIR, attr.filename)
    local_path = os.path.join(Config.DOWNLOAD_DIR, attr.filename)

    sftp.get(remote_path, local_path)

    # Keep the remote timestamp so the next run can detect changes.
    if attr.st_mtime is not None:
        os.utime(local_path, (attr.st_atime or attr.st_mtime, attr.st_mtime))
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
    with sftp_session() as sftp:
        entries = list_remote_files(sftp)
        logger.info(f"Found {len(entries)} file(s) on remote server.")

        for attr in entries:
            filename = attr.filename
            status = classify(attr)

            if status == "unchanged":
                logger.info(f"Skipping already processed file: {filename}")
                summary["skipped"].append(filename)
                continue
            if status == "changed":
                logger.info(f"File changed on remote, downloading again: {filename}")

            try:
                local_path = download_file(sftp, attr)
                move_to_processed(local_path, filename)
                logger.info(f"Transferred: {filename}")
                summary["downloaded"].append(filename)
            except Exception as e:
                logger.error(f"Failed to transfer {filename}: {e}")
                summary["errors"].append(filename)

    return summary
