# MBA Schedule Telegram Bot

A Telegram bot that sends **daily reminders** for the MBA Spring 2026 schedule. The night before each day, she gets a breakdown of what’s due: assignments get an optional **AI briefing**, and classes/quizzes get a simple “you have this at this time” message.

## Features

- **Daily reminder** (default 8pm) with everything due **tomorrow**
- **Assignments** – short briefing from OpenAI when API key is set, or from `details` in `schedule.json` when it’s not
- **Classes / quizzes / exams** – one-line reminders with course and time
- **Commands:** `/today` · `/tomorrow` · `/week` · `/assignment` · `/start` · `/unsubscribe` · `/help` · `/chatid`

---

## Where to run it (hosting)

The bot must **run 24/7** (or at least be running when the reminder time hits) so the daily message is sent on schedule.

| Option | Will reminders always fire on the scheduled date? |
|--------|---------------------------------------------------|
| **Run locally** (your Mac/PC) | **Yes** – as long as the computer is on and `python bot.py` (or the app) is running at reminder time (e.g. 8pm). If the machine is asleep or the script is stopped, that day’s reminder is skipped. |
| **Docker on your machine** | **Yes** – if Docker is running 24/7 and the container is up. Same idea: the process must be running at 8pm (or whatever you set). Use `restart: unless-stopped` so it comes back after reboot. |
| **VPS / cloud (e.g. a $5 droplet)** | **Yes** – best for “always on”. Run the bot or Docker there; reminders will fire every day as long as the server is up. |
| **Raspberry Pi** | **Yes** – if it’s always on and the bot (or Docker) is running. |

So: **running locally is fine** and it will deliver on the scheduled date **when the app is running at that time**. If you don’t have a Pi or VPS, **Docker on a machine that’s usually on** (e.g. your laptop when you’re home, or a desktop) works: **if Docker is always running and the container is up, the bot will send the reminder every day at the set time.**

---

## Setup

### 1. Create a Telegram bot

- In Telegram, search for **@BotFather**
- Send `/newbot`, follow the prompts, and copy the **bot token**

### 2. Get her chat ID (easiest way)

1. She opens your bot in Telegram and sends **`/chatid`**.
2. The bot replies with something like: `Your chat ID is: 123456789`
3. Use that number in `.env` as `ALLOWED_CHAT_IDS=123456789` if you want only her to receive reminders.

(Alternatively: she sends any message to the bot, then you open  
`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in a browser and look for `"chat":{"id": 123456789`.)

### 3. Configure

```bash
cd mba-telegram-bot
cp .env.example .env
```

Edit `.env`:

- **TELEGRAM_BOT_TOKEN** – (required) from BotFather
- **OPENAI_API_KEY** – (optional) for AI briefings. ChatGPT Pro does *not* include API access. **Workaround without API:** add a `details` field to assignments in `schedule.json` with a short description; the bot will use that as the briefing (first 1–2 sentences) when no key is set.
- **ALLOWED_CHAT_IDS** – (optional) comma-separated chat IDs (e.g. from `/chatid`). Leave empty to let anyone who `/start` subscribe.
- **REMINDER_HOUR** / **REMINDER_MINUTE** – (optional) daily reminder time (default 20:00 = 8pm). With Docker, the container uses **America/Vancouver** so 8pm is Vancouver/BC time.

---

## Run the bot

### Option A: Local (no Docker)

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

Keep this terminal (and machine) running at reminder time.

### Option B: Docker (runs 24/7 as long as Docker is running)

```bash
docker compose up -d --build
```

- Reminders will fire every day at the set time **as long as the container is running**.
- `restart: unless-stopped` in `docker-compose.yml` restarts the bot after a reboot (if Docker starts on boot).
- Logs: `docker compose logs -f mba-bot`

### Option C: Free 24/7 hosting (good for one user)

If your laptop sleeps and you want reminders to always fire, run the bot on a **free always-on server**. One person using it fits easily in free tiers.

**Oracle Cloud Free Tier** (no charge if you stay in free limits):

1. Sign up at **[signup.cloud.oracle.com](https://signup.cloud.oracle.com/)** (Free Tier; card used for verification only, not charged if you stay in Always Free). Then in the Oracle Cloud console create a **Compute** VM (e.g. Ubuntu 22.04, 1 GB RAM is enough).
2. SSH into the VM and install Docker:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER
   # log out and back in, or: newgrp docker
   ```
3. Copy your bot to the server (e.g. `scp -r mba-telegram-bot user@<VM-IP>:~/` or clone from GitHub if you push the repo). Copy your `.env` with `TELEGRAM_BOT_TOKEN` and `ALLOWED_CHAT_IDS`.
4. On the server:
   ```bash
   cd ~/mba-telegram-bot
   docker compose up -d --build
   ```
5. Reminders run 24/7. With Docker, the app uses **America/Vancouver** by default, so `REMINDER_HOUR=20` = 8pm Vancouver/BC. On a bare server (no Docker) set `TZ=America/Vancouver` in the environment if you want 8pm Pacific.

**Other free options:** Google Cloud or AWS free tier (small VM) – same idea: Linux + Docker + this repo + `.env`.

### Option D: Fly.io (free tier)

**Install flyctl (run these in your terminal):**

- **Mac without Homebrew:**  
  ```bash
  curl -L https://fly.io/install.sh | sh
  ```  
  Then add flyctl to your PATH. Either let the script add it when it asks, or run once:
  ```bash
  echo 'export PATH="$HOME/.fly/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
  ```
- **Mac with Homebrew:** `brew install flyctl`

Check it worked: `fly version`. Then log in: `fly auth login`.

**Deploy steps:**

1. In the project directory run: `fly launch`
2. When it asks **"Choose an app name"**, type something **unique** (e.g. `mba-bot-yourname-99`). Lowercase, numbers, hyphens only. Say **no** to PostgreSQL.
3. **Set your Telegram token:** `fly secrets set TELEGRAM_BOT_TOKEN=your_bot_token_here`  
   Optional: `fly secrets set ALLOWED_CHAT_IDS=her_chat_id`
4. Deploy: `fly deploy`

**If you still see "failed to create app":**

- **Name taken:** Try a different name when Fly asks (e.g. add numbers: `mba-bot-cu-2026`).
- **Payment method:** Fly often requires a card on file even for free tier. Add one at [fly.io/dashboard](https://fly.io/dashboard) → Account → Billing; you won’t be charged if you stay within free limits.
- **See the real error:** Run `fly apps create test-mba-bot-xyz123` in a terminal. If it fails, the message (e.g. “payment required” or “name taken”) will tell you what’s wrong.

**If you see "unable to deploy" or the app crashes:**

- **Set the token:** Run `fly secrets set TELEGRAM_BOT_TOKEN=<token>` then `fly deploy` again.
- **Check logs:** `fly logs` – you should see "Bot running. Reminders at ...".

Reminders use Vancouver time (8pm Pacific) by default via `TZ=America/Vancouver` in `fly.toml`.

---

## Schedule data

Events are in `schedule.json`. You can edit that file to add or change dates, courses, titles, and types. Each event can have:

- `date` – `YYYY-MM-DD`
- `course` – e.g. "Marketing", "Accounting"
- `title` – short description
- `type` – `assignment` | `class` | `quiz` | `exam` | `discussion` | `presentation`
- `time_note` – e.g. "before class", "midnight"
- `details` – (optional) short description for assignments; shown as briefing (with or without OpenAI)
