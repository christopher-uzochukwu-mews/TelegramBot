"""
MBA Schedule Telegram Bot – daily reminders and optional AI briefings.
"""
import json
import logging
from datetime import date, timedelta, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from briefing import get_assignment_briefing
from config import (
    ALLOWED_CHAT_IDS,
    HEALTH_CHECK_PORT,
    REMINDER_HOUR,
    REMINDER_MINUTE,
    SCHEDULE_PATH,
    TELEGRAM_BOT_TOKEN,
)
from messages import (
    format_event_short,
    format_event_with_briefing,
    format_next_assignment_message,
    format_today_message,
    format_tomorrow_message,
    format_week_message,
)
from schedule_loader import format_date_for_display, get_events_tomorrow, load_schedule

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SUBSCRIBERS_PATH = Path(__file__).parent / "subscribers.json"


def _run_health_server(port: int) -> None:
    ROOT_HTML = b"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MBA Schedule Bot</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Georgia, 'Times New Roman', serif; background: #faf8f5; color: #2c2522; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
  .card { max-width: 28rem; text-align: center; }
  .card h1 { font-size: 1.125rem; font-weight: 600; color: #2c2522; margin-bottom: 0.5rem; }
  .card p { font-size: 0.95rem; line-height: 1.6; color: #5a524e; }
  .card .links { margin-top: 2rem; font-size: 0.875rem; }
  .card .links a { color: #8b4d5a; text-decoration: none; }
  .card .links a:hover { text-decoration: underline; }
  .card .links span { color: #999; margin: 0 0.5rem; }
</style></head>
<body>
<div class="card">
  <h1>MBA Schedule Telegram Bot</h1>
  <p>Built by Christopher Uzochukwu for his wife — for her MBA program at Vancouver Island University, Nanaimo. Sends daily reminders and answers commands in Telegram.</p>
  <p class="links"><a href="/love">For Chiamaka</a> <span>&middot;</span> <a href="/health">Health</a></p>
</div>
</body></html>
"""
    love_page_path = Path(__file__).parent / "chiamaka-page" / "index.html"
    try:
        LOVE_HTML = love_page_path.read_bytes()
    except OSError:
        LOVE_HTML = None

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0].rstrip("/") or "/"
            if path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            elif path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(ROOT_HTML)
            elif path in ("/love", "/chiamaka") and LOVE_HTML is not None:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(LOVE_HTML)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):  # noqa: ARG002
            pass  # quiet

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def load_subscribers() -> list[int]:
    try:
        with open(SUBSCRIBERS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_subscribers(chat_ids: list[int]) -> None:
    with open(SUBSCRIBERS_PATH, "w", encoding="utf-8") as f:
        json.dump(chat_ids, f, indent=2)

def add_subscriber(chat_id: int) -> bool:
    subs = load_subscribers()
    if chat_id in subs:
        return False
    subs.append(chat_id)
    save_subscribers(subs)
    return True

def remove_subscriber(chat_id: int) -> bool:
    subs = load_subscribers()
    if chat_id not in subs:
        return False
    subs.remove(chat_id)
    save_subscribers(subs)
    return True

async def send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily job: send tomorrow's schedule to all subscribers (with optional briefings)."""
    today = date.today()
    schedule = load_schedule(SCHEDULE_PATH)
    events = get_events_tomorrow(schedule, today)
    subs = load_subscribers()
    if not subs:
        return
    for chat_id in subs:
        if ALLOWED_CHAT_IDS is not None and chat_id not in ALLOWED_CHAT_IDS:
            continue
        try:
            if not events:
                msg = format_tomorrow_message(schedule, today)
                await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
                continue
            tomorrow = today + timedelta(days=1)
            day_str = format_date_for_display(tomorrow)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📆 *Tomorrow: {day_str}*\n\nHere's what's on your list:",
                parse_mode="Markdown",
            )
            for ev in events:
                if ev.get("type") == "assignment" and ev.get("details"):
                    briefing = get_assignment_briefing(ev)
                    text = format_event_with_briefing(ev, briefing)
                else:
                    text = format_event_short(ev)
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.exception("Failed to send reminder to %s: %s", chat_id, e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if ALLOWED_CHAT_IDS is not None and chat_id not in ALLOWED_CHAT_IDS:
        await update.message.reply_text(
            "You're not authorized to use this bot. Only whitelisted chats can receive reminders."
        )
        return
    added = add_subscriber(chat_id)
    if added:
        await update.message.reply_text(
            "You're subscribed to MBA schedule reminders. I'll send you a daily rundown of "
            "what's due tomorrow (assignments get a short briefing when possible).\n\n"
            "Commands: /today, /tomorrow, /week, /assignment, /help. Send /help for the full list."
        )
    else:
        await update.message.reply_text(
            "You're already subscribed. Send /help for all commands."
        )

async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the current chat ID so the user can add it to ALLOWED_CHAT_IDS."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        await update.message.reply_text("Could not get chat ID.")
        return
    await update.message.reply_text(
        f"Your chat ID is: `{chat_id}`\n\n"
        "Add this to ALLOWED_CHAT_IDS in .env (comma-separated if you have multiple) to restrict who receives reminders.",
        parse_mode="Markdown",
    )

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    schedule = load_schedule(SCHEDULE_PATH)
    msg = format_today_message(schedule)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    schedule = load_schedule(SCHEDULE_PATH)
    msg = format_tomorrow_message(schedule)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    schedule = load_schedule(SCHEDULE_PATH)
    msg = format_week_message(schedule)
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    schedule = load_schedule(SCHEDULE_PATH)
    msg = format_next_assignment_message(schedule)
    await update.message.reply_text(msg, parse_mode="Markdown")

HELP_TEXT = """📚 *MBA Schedule Bot*

/today – what's due today
/tomorrow – what's due tomorrow
/week – what's due this week
/assignment – closest assignment(s) due
/start – subscribe to daily reminders
/unsubscribe – stop daily reminders
/chatid – show your chat ID (for allowlist)
/help – this message"""

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else 0
    removed = remove_subscriber(chat_id)
    if removed:
        await update.message.reply_text("You're unsubscribed. You won't get daily reminders. Send /start anytime to subscribe again.")
    else:
        await update.message.reply_text("You weren't subscribed. Send /start to get daily reminders.")

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (from @BotFather)")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("tomorrow", cmd_tomorrow))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("assignment", cmd_assignment))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))

    when = time(hour=REMINDER_HOUR, minute=REMINDER_MINUTE)
    app.job_queue.run_daily(send_reminders, time=when)

    health_thread = Thread(target=_run_health_server, args=(HEALTH_CHECK_PORT,), daemon=True)
    health_thread.start()
    logger.info("Health check: http://0.0.0.0:%s/health", HEALTH_CHECK_PORT)

    logger.info("Bot running. Reminders at %s daily.", when)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
