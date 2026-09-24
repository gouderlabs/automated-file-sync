# Automated File Sync

A configurable Python service that automates the daily transfer of
files between an SFTP server and local storage — with logging,
duplicate protection, scheduling, and optional failure alerts.

## The problem

In many operational environments (banking, logistics, e-commerce),
teams rely on **manual, repetitive file transfers** between systems:
someone logs into an FTP/SFTP server every day, checks for new files,
downloads them, and moves them into the right folder for processing.

This is slow, error-prone, and easy to forget — a missed transfer can
mean a delayed report, a missed reconciliation, or a broken downstream
process. It's a small task, but at scale (daily, across many file
types and partners) it adds up to real operational risk.

## What this project does

- Connects to an SFTP server on a schedule (default: once a day)
- Detects **only new files**, skipping ones already processed —
  no duplicate transfers
- Downloads files, then moves them into a `processed` folder to keep
  a clean audit trail of what has already been handled
- Logs every action (connection, transfer, skip, error) to a daily
  log file, so any run can be reviewed after the fact
- Optionally sends an email alert if a transfer fails, so issues are
  caught immediately instead of days later
- All credentials and settings are read from environment variables —
  **nothing sensitive is ever hardcoded in the code**

## Architecture

```
main.py            → entry point, runs the schedule
src/config.py       → all settings, loaded from .env
src/transfer.py      → core SFTP logic (connect, list, download, move)
src/logger.py        → daily rotating logs
src/notifier.py       → optional email alert on failure
```

## Setup

```bash
git clone <this-repo>
cd automated-file-sync
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your own SFTP server details. The default values
point to `test.rebex.net`, a public read-only demo SFTP server, so
you can run the project immediately without any credentials of your
own — useful for testing the logic end to end.

## Running it

```bash
python main.py
```

By default, it runs one sync immediately, then keeps running in the
background and repeats daily at the time set in `RUN_TIME`.

## Example log output

```
[19:00:01] INFO - Connecting to test.rebex.net:22 ...
[19:00:02] INFO - Found 4 file(s) on remote server.
[19:00:02] INFO - Skipping already processed file: readme.txt
[19:00:03] INFO - Transferred: report_2026-09-20.csv
[19:00:03] INFO - Sync summary — downloaded: 1, skipped: 3, errors: 0
[19:00:03] INFO - Connection closed.
```

## Design choices worth noting

- **No hardcoded secrets.** Every credential lives in `.env`, which
  is git-ignored. This is a small detail, but it's the difference
  between a script that's safe to share and one that isn't.
- **Idempotent by design.** Re-running the job never re-downloads a
  file that's already been processed — important for a job that runs
  unattended every day.
- **Fail loud, not silent.** Errors are logged and can trigger an
  email alert, rather than failing silently and only being noticed
  once something downstream breaks.

## What I'd add next

- Retry logic with backoff for transient network failures
- Support for multiple remote directories/sources in one config
- A small dashboard to visualize transfer history from the logs

## Background

This project reflects a type of automation I've worked on
professionally in a banking IT environment, where reliable, auditable
file transfers between systems are a routine but critical need. This
version is built from scratch with public test infrastructure and
contains no proprietary code, data, or credentials.
