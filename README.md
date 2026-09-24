# Automated File Sync

![tests](https://github.com/gouderlabs/automated-file-sync/actions/workflows/ci.yml/badge.svg)

A configurable Python service that automates the daily transfer of
files from an SFTP server to local storage — with logging, change
detection, host key verification, scheduling, and optional failure alerts.

## The problem

In many operational environments (banking, logistics, e-commerce),
teams rely on **manual, repetitive file transfers** between systems:
someone logs into an SFTP server every day, checks for new files,
downloads them, and moves them into the right folder for processing.

This is slow, error-prone, and easy to forget — a missed transfer can
mean a delayed report, a missed reconciliation, or a broken downstream
process. It's a small task, but at scale (daily, across many file
types and partners) it adds up to real operational risk.

## What this project does

- Connects to an SFTP server on a schedule (default: once a day)
- Transfers **only new or modified files**: a file is skipped when its
  size and modification time match what was already processed
- Ignores remote sub-directories instead of choking on them
- Moves each downloaded file into a `processed` folder, keeping a clear
  record of what has been handled
- Verifies the server's **host key** and refuses unknown servers by default
- Logs every action (connection, transfer, skip, error) to a log file that
  **rotates at midnight** and keeps 30 days of history
- Optionally emails an alert when a run fails
- Reads all credentials and settings from environment variables; the
  repository contains no secrets

## Architecture

```
main.py              → entry point, validates settings, runs the schedule
src/config.py        → all settings, loaded from .env
src/transfer.py      → core SFTP logic (connect, list, detect changes, download, move)
src/trust_host.py    → one-time helper to trust a server's host key
src/logger.py        → daily-rotating logs
src/notifier.py      → optional email alert on failure
tests/               → unit tests, no network required
```

## Setup

```bash
git clone https://github.com/gouderlabs/automated-file-sync.git
cd automated-file-sync
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

`.env.example` points to `test.rebex.net`, a public demo SFTP server
published for testing (its credentials are public), so you can try the
project without any account of your own. For your own server, edit `.env`.

### Trust the server (once)

By default the client only connects to servers whose key it already
knows. Save the key once, after checking the fingerprint:

```bash
python -m src.trust_host
```

For a quick throwaway test you can set `SFTP_STRICT_HOST_KEY=false`
in `.env`, but this disables protection against server impersonation and
should never be used with real data.

## Running it

```bash
python main.py
```

It runs one sync immediately (`RUN_ONCE_NOW=true`), then keeps running and
repeats every day at `RUN_TIME`.

## Running the tests

```bash
python -m unittest discover -s tests -t . -v
```

The tests use an in-memory fake SFTP server, so they run offline. They cover
new / unchanged / modified files, ignored directories, one failing file not
stopping the others, a missing remote directory, host key policy, and clean
connection shutdown on errors.

## Example output


```
INFO - Connecting to :22 ...
[2026-09-24 12:58:39] INFO - Found 1 file(s) on remote server.
[2026-09-24 12:58:39] INFO - Transferred: a.csv
[2026-09-24 12:58:39] INFO - Connecting to :22 ...
[2026-09-24 12:58:39] INFO - Found 1 file(s) on remote server.
[2026-09-24 12:58:39] INFO - Skipping already processed file: a.csv
ok
test_unchanged_file_is_not_downloaded_twice (tests.test_transfer.TestSyncBehaviour) ... [2026-09-24 12:58:39] INFO - Connecting to :22 ...
[2026-09-24 12:58:39] INFO - Found 1 file(s) on remote server.
[2026-09-24 12:58:39] INFO - Transferred: a.csv
[2026-09-24 12:58:39] INFO - Connecting to :22 ...
[2026-09-24 12:58:39] INFO - Found 1 file(s) on remote server.
[2026-09-24 12:58:39] INFO - Skipping already processed file: a.csv
ok

----------------------------------------------------------------------
Ran 19 tests in 0.271s

OK
python -m src.trust_host
SFTP_HOST is empty. Copy .env.example to .env and fill it in first.
python -m src.trust_host
Contacting test.rebex.net:22 ...
Key type   : ssh-ed25519
Fingerprint: SHA256:d7Te2DHmvBNSWJNBWik2KbDTjmWtYHe2bvXTMM9lVg4
Trust this key and save it to 'known_hosts'? [y/N] yes
Saved. You can now run: python main.py
After python main.py
[2026-09-24 13:01:19] INFO - Running an immediate sync before starting the schedule...
[2026-09-24 13:01:19] INFO - Connecting to test.rebex.net:22 ...
[2026-09-24 13:01:22] INFO - Found 16 file(s) on remote server.
[2026-09-24 13:01:23] INFO - Transferred: imap-console-client.png
[2026-09-24 13:01:24] INFO - Transferred: KeyGenerator.png
[2026-09-24 13:01:25] INFO - Transferred: KeyGeneratorSmall.png
[2026-09-24 13:01:26] INFO - Transferred: mail-editor.png
[2026-09-24 13:01:27] INFO - Transferred: mail-send-winforms.png
[2026-09-24 13:01:28] INFO - Transferred: mime-explorer.png
[2026-09-24 13:01:29] INFO - Transferred: pocketftp.png
[2026-09-24 13:01:30] INFO - Transferred: pocketftpSmall.png
[2026-09-24 13:01:31] INFO - Transferred: pop3-browser.png
[2026-09-24 13:01:32] INFO - Transferred: pop3-console-client.png
[2026-09-24 13:01:33] INFO - Transferred: readme.txt
[2026-09-24 13:01:33] INFO - Transferred: ResumableTransfer.png
[2026-09-24 13:01:34] INFO - Transferred: winceclient.png
[2026-09-24 13:01:35] INFO - Transferred: winceclientSmall.png
[2026-09-24 13:01:36] INFO - Transferred: WinFormClient.png
[2026-09-24 13:01:37] INFO - Transferred: WinFormClientSmall.png
[2026-09-24 13:01:37] INFO - Connection closed.
[2026-09-24 13:01:37] INFO - Sync summary — downloaded: 16, skipped: 0, errors: 0
[2026-09-24 13:01:37] INFO - Scheduler started. Job will run daily at 19:00.
```

## Design choices worth noting

- **No secrets in the code or the repo.** Credentials live in `.env`, which
  is git-ignored; `.env.example` only contains the public demo server's.
- **Idempotent.** Re-running the job never re-downloads a file that hasn't
  changed, which matters for a job that runs unattended every day.
- **Secure by default.** Unknown or changed host keys are rejected, with an
  explicit log message explaining what to do.
- **Fail loud, not silent.** A single failing file doesn't stop the run but
  is reported and retried next time; a missing remote directory or a failed
  connection aborts the run, is logged, and triggers the alert if enabled.
- **Always cleans up.** The SSH connection is closed even when a run crashes.

## Known limitations / what I'd add next

- Retry with exponential backoff for transient network failures
- State is inferred from the `processed` folder: if another system empties or
  renames that folder, files will be downloaded again. A small SQLite or JSON
  state file would remove that coupling
- Multiple remote directories / sources in one configuration
- Key-based authentication (only passwords are supported today)
- Run as a container or a system service (cron/systemd) instead of an
  in-process scheduler, so a crash is restarted automatically

## Background

This project reflects a type of automation I've worked on
professionally in a banking IT environment, where reliable, auditable
file transfers between systems are a routine but critical need. This
version is built from scratch with public test infrastructure and
contains no proprietary code, data, or credentials.
