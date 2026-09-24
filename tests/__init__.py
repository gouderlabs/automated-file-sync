"""Test package. Sends logs to a temp dir so tests never write into ./logs."""

import os
import tempfile

os.environ["LOG_DIR"] = tempfile.mkdtemp(prefix="filesync_test_logs_")
