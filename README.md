# gContacts2logseq

One-way sync Google Contacts to Logseq, running on a schedule via Docker.

A Python script that uses the [Google People API](https://developers.google.com/people/quickstart/python) to generate `.md` files consumable by [Logseq](https://logseq.com). Each contact becomes a page with properties for phone, email, job, company, groups, addresses (with embedded Google Maps), and a link back to Google Contacts.

---

## Requirements

- Python 3.11+ (for running locally) or Docker
- A Google Cloud project with the People API enabled and an OAuth 2.0 client ID (`credentials.json`)

---

## First-time authentication

Authentication must be done **outside Docker** — it opens a browser flow that cannot run inside a container.

1. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Set the contacts output directory and run once:
   ```bash
   export LOGSEQ_CONTACTS_DIR="/mnt/c/Users/spiros/Contacts"
   python gContacts2logseq.py
   ```

3. Copy the printed URL into your browser, complete the Google authorization flow, then close the tab. A `token.json` file is written to the current directory.

4. Verify the token includes a refresh token:
   ```bash
   python -c "import json; d=json.load(open('token.json')); print('OK' if d.get('refresh_token') else 'MISSING refresh_token')"
   ```

After this, the script (and Docker container) will silently refresh the token on each run.

---

## Running locally

```bash
export LOGSEQ_CONTACTS_DIR="/mnt/c/Users/spiros/Contacts"
python gContacts2logseq.py
```

`token.json` and `credentials.json` are read from the current directory by default. Set `SYNC_INTERVAL_SECONDS=0` to run once and exit instead of looping.

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
