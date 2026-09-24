"""
Tests for the sync engine. No network needed: the SFTP server is replaced
by a small in-memory fake.

Run:  python -m unittest discover -s tests -t . -v
"""

import os
import stat
import tempfile
import unittest
from contextlib import contextmanager
from unittest import mock

import paramiko

from src import transfer
from src.config import Config

T0 = 1_700_000_000  # an arbitrary remote modification time


class FakeSFTP:
    """Minimal stand-in for paramiko.SFTPClient.

    `files` maps name -> (content_bytes, mtime), or name -> None for a directory.
    """

    def __init__(self, files, fail_on=()):
        self.files = files
        self.fail_on = set(fail_on)
        self.get_calls = []

    def listdir_attr(self, path):
        entries = []
        for name, entry in self.files.items():
            attr = paramiko.SFTPAttributes()
            attr.filename = name
            if entry is None:
                attr.st_mode, attr.st_size, attr.st_mtime = stat.S_IFDIR | 0o755, 0, T0
            else:
                data, mtime = entry
                attr.st_mode = stat.S_IFREG | 0o644
                attr.st_size, attr.st_mtime = len(data), mtime
            attr.st_atime = attr.st_mtime
            entries.append(attr)
        return entries

    def get(self, remote_path, local_path):
        name = remote_path.rsplit("/", 1)[-1]
        self.get_calls.append(name)
        if name in self.fail_on:
            raise IOError("simulated network failure")
        with open(local_path, "wb") as f:
            f.write(self.files[name][0])


class SyncTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.download_dir = os.path.join(self.tmp.name, "downloaded")
        self.processed_dir = os.path.join(self.tmp.name, "processed")
        for attr, value in {
            "DOWNLOAD_DIR": self.download_dir,
            "PROCESSED_DIR": self.processed_dir,
            "SFTP_REMOTE_DIR": "/remote",
        }.items():
            patcher = mock.patch.object(Config, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_with(self, fake):
        @contextmanager
        def fake_session():
            yield fake

        with mock.patch.object(transfer, "sftp_session", fake_session):
            return transfer.run_sync()

    def processed(self, name):
        return os.path.join(self.processed_dir, name)


class TestSyncBehaviour(SyncTestCase):
    def test_new_file_is_downloaded_and_moved_to_processed(self):
        fake = FakeSFTP({"a.csv": (b"hello", T0)})
        summary = self.run_with(fake)

        self.assertEqual(summary["downloaded"], ["a.csv"])
        with open(self.processed("a.csv"), "rb") as f:
            self.assertEqual(f.read(), b"hello")
        self.assertFalse(os.path.exists(os.path.join(self.download_dir, "a.csv")))
        # remote timestamp is preserved, which is what makes change detection work
        self.assertEqual(int(os.stat(self.processed("a.csv")).st_mtime), T0)

    def test_unchanged_file_is_not_downloaded_twice(self):
        fake = FakeSFTP({"a.csv": (b"hello", T0)})
        self.run_with(fake)
        summary = self.run_with(fake)

        self.assertEqual(summary["downloaded"], [])
        self.assertEqual(summary["skipped"], ["a.csv"])
        self.assertEqual(fake.get_calls, ["a.csv"])  # fetched only once overall

    def test_file_with_different_size_is_downloaded_again(self):
        self.run_with(FakeSFTP({"a.csv": (b"v1", T0)}))
        summary = self.run_with(FakeSFTP({"a.csv": (b"version two", T0 + 60)}))

        self.assertEqual(summary["downloaded"], ["a.csv"])
        with open(self.processed("a.csv"), "rb") as f:
            self.assertEqual(f.read(), b"version two")

    def test_same_size_but_newer_mtime_is_downloaded_again(self):
        self.run_with(FakeSFTP({"a.csv": (b"AAAA", T0)}))
        summary = self.run_with(FakeSFTP({"a.csv": (b"BBBB", T0 + 3600)}))

        self.assertEqual(summary["downloaded"], ["a.csv"])
        with open(self.processed("a.csv"), "rb") as f:
            self.assertEqual(f.read(), b"BBBB")

    def test_tiny_timestamp_difference_is_tolerated(self):
        self.run_with(FakeSFTP({"a.csv": (b"AAAA", T0)}))
        summary = self.run_with(FakeSFTP({"a.csv": (b"AAAA", T0 + 1)}))

        self.assertEqual(summary["skipped"], ["a.csv"])

    def test_remote_directories_are_ignored(self):
        fake = FakeSFTP({"subdir": None, "a.csv": (b"x", T0)})
        summary = self.run_with(fake)

        self.assertEqual(summary["downloaded"], ["a.csv"])
        self.assertEqual(summary["errors"], [])

    def test_one_failing_file_does_not_stop_the_others(self):
        fake = FakeSFTP(
            {"bad.csv": (b"x", T0), "good.csv": (b"y", T0)}, fail_on={"bad.csv"}
        )
        summary = self.run_with(fake)

        self.assertEqual(summary["errors"], ["bad.csv"])
        self.assertEqual(summary["downloaded"], ["good.csv"])
        self.assertFalse(os.path.exists(self.processed("bad.csv")))
        # a failed file is retried on the next run
        summary = self.run_with(FakeSFTP({"bad.csv": (b"x", T0), "good.csv": (b"y", T0)}))
        self.assertEqual(summary["downloaded"], ["bad.csv"])

    def test_missing_remote_directory_fails_loudly(self):
        fake = FakeSFTP({})
        fake.listdir_attr = mock.Mock(side_effect=FileNotFoundError())
        with self.assertRaises(FileNotFoundError):
            self.run_with(fake)


class TestConnection(unittest.TestCase):
    def test_strict_mode_rejects_unknown_hosts(self):
        with mock.patch.object(Config, "SFTP_STRICT_HOST_KEY", True), mock.patch.object(
            transfer.paramiko, "SSHClient"
        ) as ssh_client:
            transfer.build_client()
        policy = ssh_client.return_value.set_missing_host_key_policy.call_args[0][0]
        self.assertIsInstance(policy, paramiko.RejectPolicy)

    def test_known_hosts_file_is_loaded_when_it_exists(self):
        with tempfile.NamedTemporaryFile() as known_hosts:
            with mock.patch.object(Config, "SFTP_STRICT_HOST_KEY", True), mock.patch.object(
                Config, "SFTP_KNOWN_HOSTS", known_hosts.name
            ), mock.patch.object(transfer.paramiko, "SSHClient") as ssh_client:
                transfer.build_client()
        ssh_client.return_value.load_host_keys.assert_called_once_with(known_hosts.name)

    def test_non_strict_mode_is_explicit_opt_in(self):
        with mock.patch.object(Config, "SFTP_STRICT_HOST_KEY", False), mock.patch.object(
            transfer.paramiko, "SSHClient"
        ) as ssh_client:
            transfer.build_client()
        policy = ssh_client.return_value.set_missing_host_key_policy.call_args[0][0]
        self.assertIsInstance(policy, paramiko.AutoAddPolicy)

    def test_client_is_closed_when_the_job_fails_midway(self):
        client = mock.MagicMock()
        with mock.patch.object(transfer, "build_client", return_value=client):
            with self.assertRaises(RuntimeError):
                with transfer.sftp_session():
                    raise RuntimeError("boom")
        client.open_sftp.return_value.close.assert_called_once()
        client.close.assert_called_once()

    def test_client_is_closed_when_connection_fails(self):
        client = mock.MagicMock()
        client.connect.side_effect = paramiko.SSHException("Server 'x' not found in known_hosts")
        with mock.patch.object(transfer, "build_client", return_value=client):
            with self.assertRaises(paramiko.SSHException):
                with transfer.sftp_session():
                    pass
        client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
