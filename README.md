# gContacts2logseq

One-way sync Google Contacts to Logseq, running on a schedule via Docker.

A Python script that uses the [Google People API](https://developers.google.com/people/quickstart/python) to generate `.md` files consumable by [Logseq](https://logseq.com). Each contact becomes a page with properties for phone, email, job, company, groups, addresses (with embedded Google Maps), and a link back to Google Contacts.

---

## Requirements

- Python 3.11+ (for running locally) or Docker
- A Google Cloud project with the People API enabled and an OAuth 2.0 client ID (`credentials.json`)

---

## First-time authentication

When no valid token exists — on first run, or after a token is revoked — the script automatically starts an OAuth flow on port **8080** and prints a URL to the logs. Open the URL in your browser, complete the Google authorization, and the token is saved automatically. The sync then starts immediately.

This works both when running locally and inside Docker (port 8080 is exposed in `docker-compose.yml`).

---

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export LOGSEQ_CONTACTS_DIR="/mnt/c/Users/spiros/Contacts"
python gContacts2logseq.py
```

`token.json` and `credentials.json` are read from the current directory by default. If `token.json` is missing, the OAuth flow starts automatically on port 8080. Set `SYNC_INTERVAL_SECONDS=0` to run once and exit instead of looping.

---

## Running with Docker

1. Copy `.env.example` to `.env` and set `LOGSEQ_CONTACTS_DIR`:
   ```bash
   cp .env.example .env
   ```

2. Build and start:
   ```bash
   docker compose up -d --build
   ```

The container mounts `credentials.json` and `token.json` from the project directory, and the Logseq contacts folder from your host. It syncs on startup and then every `SYNC_INTERVAL_SECONDS` (default: 1 hour). Logs go to stdout:

```bash
docker compose logs -f
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LOGSEQ_CONTACTS_DIR` | *(required)* | Absolute path to the Logseq contacts directory |
| `SYNC_INTERVAL_SECONDS` | `3600` | Seconds between syncs. `0` = run once and exit |
| `TOKEN_FILE` | `token.json` | Path to the OAuth token file |
| `CREDENTIALS_FILE` | `credentials.json` | Path to the Google OAuth client secret file |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Token expiry

If the token is revoked (e.g. after 6 months of inactivity, or if you exceed Google's token limit for test-mode OAuth apps), you will see an `invalid_grant` error in the logs. Delete `token.json` and repeat the first-time authentication steps above.
