"""
trust_host.py
-------------
One-time helper: fetch the SFTP server's host key, show its fingerprint,
and save it to SFTP_KNOWN_HOSTS once you confirm it.

    python -m src.trust_host

Cross-platform on purpose (no `ssh-keyscan`, no shell redirection).
Ideally, compare the fingerprint with the one your server administrator
gave you before answering "yes".
"""

import base64
import hashlib
import sys

import paramiko

from src.config import Config


def fingerprint(key) -> str:
    """OpenSSH-style SHA256 fingerprint of a host key."""
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def host_pattern(host: str, port: int) -> str:
    """known_hosts entry name: bare host on port 22, '[host]:port' otherwise."""
    return host if port == 22 else f"[{host}]:{port}"


def fetch_host_key(host: str, port: int, timeout: int):
    transport = paramiko.Transport((host, port))
    try:
        transport.start_client(timeout=timeout)
        return transport.get_remote_server_key()
    finally:
        transport.close()


def main() -> int:
    if not Config.SFTP_HOST:
        print("SFTP_HOST is empty. Copy .env.example to .env and fill it in first.")
        return 1

    host, port = Config.SFTP_HOST, Config.SFTP_PORT
    print(f"Contacting {host}:{port} ...")
    key = fetch_host_key(host, port, Config.SFTP_TIMEOUT)

    print(f"Key type   : {key.get_name()}")
    print(f"Fingerprint: {fingerprint(key)}")
    answer = input(f"Trust this key and save it to '{Config.SFTP_KNOWN_HOSTS}'? [y/N] ")
    if answer.strip().lower() not in ("y", "yes"):
        print("Aborted, nothing saved.")
        return 1

    host_keys = paramiko.HostKeys()
    try:
        host_keys.load(Config.SFTP_KNOWN_HOSTS)
    except IOError:
        pass  # file doesn't exist yet
    host_keys.add(host_pattern(host, port), key.get_name(), key)
    host_keys.save(Config.SFTP_KNOWN_HOSTS)
    print(f"Saved. You can now run: python main.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
