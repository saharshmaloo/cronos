# Cronos

A personal coaching app delivered entirely through Telegram. Cronos checks in with you every hour, asks what you've been doing, gives you blunt feedback, and keeps your Google Tasks front and center. Built to run 24/7 on AWS EC2.

---

## How It Works

- **Hourly check-ins**: At the top of every hour, Cronos messages you asking what you've been up to. It cross-references your open Google Tasks and calls you out if you're slacking.
- **Feedback loop**: When you respond, it gives immediate feedback based on what you said — no sugarcoating.
- **On-demand conversation**: Message it any time for accountability, task prioritization, or a reality check.
- **Pause logic**: If you don't respond to 2 consecutive hourly prompts, it backs off for 8 hours. The moment you message it, prompts resume.
- **Context-aware**: Every response is informed by your Google Tasks, your conversation history, and a programmable tone/personality.
- **Daily rating**: At the end of each day, Cronos rates your performance relative to your recent baseline — `better`, `neutral`, or `worse` — with a one-sentence justification. Ratings are injected into future check-ins so the coach can hold a longer-term standard.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12+ |
| Framework | FastAPI + uvicorn |
| Database | SQLite via SQLAlchemy 2.0 |
| Migrations | Alembic |
| Messaging | Telegram Bot API |
| AI | Anthropic Claude (`claude-sonnet-4-6`) |
| Google | `google-api-python-client` + `google-auth-oauthlib` |
| Scheduler | APScheduler v3 |
| Package mgr | uv |
| Hosting | AWS EC2 (t3.micro, Ubuntu 22.04) |

---

## Project Structure

```
cronos/
├── app/
│   ├── main.py                  # FastAPI app entry point + lifespan
│   ├── models.py                # SQLAlchemy ORM models
│   ├── database.py              # Engine + session factory
│   ├── config.py                # Settings (env vars) + app_config DB helpers
│   ├── agent/
│   │   └── coach.py             # Claude context assembly + API call
│   ├── integrations/
│   │   ├── telegram_client.py   # send_message() + set_webhook()
│   │   └── google_tasks.py      # OAuth token management + fetch_active_tasks()
│   ├── routes/
│   │   ├── webhook.py           # POST /webhook/telegram
│   │   └── health.py            # GET /health
│   └── scheduler/
│       ├── jobs.py              # APScheduler setup
│       └── hourly_prompt.py     # Hourly check-in logic + pause logic
├── scripts/
│   ├── google_auth.py           # One-time Google OAuth flow
│   ├── telegram_setup.py        # Register Telegram webhook URL
│   └── set_tone.py              # Update coach personality in DB
├── deploy/
│   ├── cronos.service           # systemd unit file
│   └── nginx.conf               # nginx reverse proxy config
├── alembic/                     # DB migration files
├── alembic.ini
├── pyproject.toml
└── .env.example
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values. Do not add inline comments — `.env` does not support them.

```
DATABASE_URL=sqlite:///./data/coach.db
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=              # leave blank — auto-detected from your first message to the bot
TELEGRAM_WEBHOOK_SECRET=       # optional but recommended — alphanumeric, _ and - only
TIMEZONE=America/New_York
CONTEXT_WINDOW_MESSAGES=20
PORT=8000
```

---

## Initial Setup

### 1. Install dependencies

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 2. Create the database

```bash
mkdir -p data
uv run alembic upgrade head
```

### 3. Google Tasks OAuth (one-time)

- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a project → enable **Google Tasks API**
- Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
- Application type: **Desktop App**
- Copy the `client_id` and `client_secret` into `.env`
- Add your Google account as a test user under **OAuth consent screen → Test users**

Then run:
```bash
uv run python scripts/google_auth.py
```

On a headless server (EC2): the script prints an auth URL. Open it in your local browser, approve access, then copy the `http://localhost:1/?code=...` URL from the address bar and paste it back into the terminal.

### 4. Create a Telegram bot

- Message [@BotFather](https://t.me/BotFather) on Telegram
- Send `/newbot` and follow the prompts
- Copy the bot token into `.env` as `TELEGRAM_BOT_TOKEN`

### 5. Register the Telegram webhook

```bash
uv run python scripts/telegram_setup.py https://yourdomain.com
```

Your `TELEGRAM_WEBHOOK_SECRET` (if set) must be registered at the same time. If you change it later, re-run this script.

### 6. Run locally

```bash
uv run uvicorn app.main:app --reload
```

Use [ngrok](https://ngrok.com) to expose it for local Telegram testing:
```bash
ngrok http 8000
uv run python scripts/telegram_setup.py https://xxxx.ngrok-free.app
```

Message your bot — your chat ID is auto-detected and stored on the first message.

---

## EC2 Deployment

### Instance setup

- Launch **t3.micro**, Ubuntu 22.04
- Allocate an **Elastic IP** and associate it
- Security group: open ports 22, 80, 443
- Buy a domain, point its A record to the Elastic IP

### Server setup

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx git
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

git clone https://github.com/YOUR_USERNAME/cronos.git /opt/cronos
cd /opt/cronos
cp /path/to/.env .env
uv sync
uv run alembic upgrade head
uv run python scripts/google_auth.py
```

### nginx + HTTPS

```bash
sudo tee /etc/nginx/sites-available/cronos > /dev/null << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/cronos /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

### systemd service

```bash
sudo cp deploy/cronos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cronos
sudo systemctl start cronos
```

### Register webhook

```bash
uv run python scripts/telegram_setup.py https://yourdomain.com
```

### Verify

```bash
sudo systemctl status cronos
sudo journalctl -u cronos -f
curl https://yourdomain.com/health
```

### Deploying updates

```bash
git pull && uv sync && sudo systemctl restart cronos
```

---

## Changing the Coach Personality

Edit `DEFAULT_TONE` in `app/config.py`, then run:

```bash
uv run python scripts/set_tone.py
```

This updates the tone in the database immediately without a restart.

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `messages` | All inbound and outbound messages (conversation history) |
| `google_tokens` | OAuth2 access + refresh tokens for Google Tasks |
| `tasks_cache` | Local snapshot of Google Tasks, refreshed each Claude call |
| `app_config` | Key-value settings: tone, pause state, hourly toggle, chat ID |
| `daily_ratings` | End-of-day performance ratings (`better` / `neutral` / `worse`) with one-sentence summary |

### Useful SQLite queries

```bash
# View recent messages
sqlite3 data/coach.db "SELECT created_at, direction, body FROM messages ORDER BY created_at DESC LIMIT 20;"

# Toggle hourly prompts off
sqlite3 data/coach.db "UPDATE app_config SET value = 'false' WHERE key = 'hourly_prompts_enabled';"

# Clear a pause manually
sqlite3 data/coach.db "UPDATE app_config SET value = '' WHERE key = 'paused_until';"

# Check current tone
sqlite3 data/coach.db "SELECT value FROM app_config WHERE key = 'tone_context';"
```

---

## Extensions

### Accountability Partner

Add a second Telegram chat ID that receives a daily digest — daily rating, summary, and any missed check-ins — without having access to the full conversation log.

**What to build:**

- Add `TELEGRAM_PARTNER_CHAT_ID` to `.env` and `config.py`.
- In `scheduler/hourly_prompt.py`, after recording a missed check-in, send a nudge to the partner chat: `"[user] missed their check-in at 3 PM."`.
- At end-of-day (alongside the daily rating job), call `telegram_client.send_message(partner_chat_id, digest)` where the digest is the rating + summary from `generate_daily_rating`.
- Optionally forward inbound messages from the partner's chat ID to the main user as a relay (tag them `[partner]` in the system prompt so the coach knows the source).

**Schema changes:** none required — partner chat ID lives in env/config. If you want the partner to send commands (e.g. `/streak`), add a `partner_chat_id` key to `app_config` so it can be toggled at runtime.

---

### Multi-User Support

Run one bot for multiple independent users, each with their own conversation history, Google Tasks OAuth, config, and daily ratings.

**What to build:**

**1. Add a `user_id` (Telegram chat ID) column to every per-user table:**

```sql
ALTER TABLE messages    ADD COLUMN user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE google_tokens ADD COLUMN user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE tasks_cache ADD COLUMN user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE app_config  ADD COLUMN user_id TEXT NOT NULL DEFAULT '';
ALTER TABLE daily_ratings ADD COLUMN user_id TEXT NOT NULL DEFAULT '';
```

Create a new Alembic migration for this. All existing queries must be scoped by `user_id`.

**2. Route every webhook event by `chat_id`:**

In `routes/webhook.py`, extract `chat_id` from the Telegram payload and pass it through to every DB query and coach call. Remove the global `TELEGRAM_CHAT_ID` env var — any Telegram user who messages the bot gets their own session auto-provisioned.

**3. Per-user Google OAuth:**

`scripts/google_auth.py` must accept a `--user-id` flag and store the resulting token under that `user_id` in `google_tokens`. At runtime, `google_tasks.py` looks up the token by `user_id`.

**4. Scheduler:**

The hourly job currently sends one message. Replace it with a loop over all distinct `user_id` values that have `hourly_prompts_enabled = true`, running the existing per-user check-in logic for each.

**5. `app_config` composite key:**

Change the primary key from `(key)` to `(user_id, key)` so each user has independent tone, pause state, etc.

**Minimal path:** scope `messages`, `app_config`, and `google_tokens` by `user_id` first. `tasks_cache` and `daily_ratings` follow the same pattern and can come later.