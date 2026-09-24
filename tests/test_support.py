"""Tests for config validation, log rotation and the trust_host helpers."""

import base64
import hashlib
import logging
import unittest
from logging.handlers import TimedRotatingFileHandler
from unittest import mock

from src import trust_host
from src.config import Config
from src.logger import get_logger


class TestConfig(unittest.TestCase):
    def test_reports_every_missing_required_setting(self):
        empty = {"SFTP_HOST": "", "SFTP_USERNAME": "", "SFTP_PASSWORD": "", "SFTP_REMOTE_DIR": ""}
        patchers = [mock.patch.object(Config, k, v) for k, v in empty.items()]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        self.assertEqual(
            sorted(Config.missing_settings()),
            ["SFTP_HOST", "SFTP_PASSWORD", "SFTP_REMOTE_DIR", "SFTP_USERNAME"],
        )

    def test_no_missing_settings_when_all_are_filled(self):
        full = {"SFTP_HOST": "h", "SFTP_USERNAME": "u", "SFTP_PASSWORD": "p", "SFTP_REMOTE_DIR": "/d"}
        patchers = [mock.patch.object(Config, k, v) for k, v in full.items()]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        self.assertEqual(Config.missing_settings(), [])


class TestLogger(unittest.TestCase):
    def test_log_file_rotates_daily_instead_of_being_fixed_at_startup(self):
        logger = get_logger()
        rotating = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
        self.assertEqual(len(rotating), 1)
        self.assertEqual(rotating[0].when, "MIDNIGHT")

    def test_get_logger_does_not_stack_handlers(self):
        before = len(get_logger().handlers)
        self.assertEqual(len(get_logger().handlers), before)
        self.assertIsInstance(get_logger(), logging.Logger)


class TestTrustHostHelpers(unittest.TestCase):
    def test_fingerprint_matches_openssh_sha256_format(self):
        key = mock.Mock()
        key.asbytes.return_value = b"fake-public-key-bytes"
        expected = base64.b64encode(hashlib.sha256(b"fake-public-key-bytes").digest()).decode().rstrip("=")
        self.assertEqual(trust_host.fingerprint(key), "SHA256:" + expected)

    def test_host_pattern_uses_brackets_only_for_non_default_ports(self):
        self.assertEqual(trust_host.host_pattern("example.com", 22), "example.com")
        self.assertEqual(trust_host.host_pattern("example.com", 2222), "[example.com]:2222")


if __name__ == "__main__":
    unittest.main()
