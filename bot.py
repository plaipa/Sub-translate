"""Telegram bot: send a subtitle file (.srt/.vtt), pick a language, get it back translated."""
from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import PurePath

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import subtitles
from translators import (LANGUAGES, ClaudeTranslator, GeminiTranslator, GoogleTranslator,
                         translate_all)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines contain the bot token URL
MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {".srt", ".vtt"}
# Comma-separated Telegram user IDs; empty = anyone (anyone can spend your API credit).
ALLOWED_USERS = {int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip()}


def permitted(update: Update) -> bool:
    return not ALLOWED_USERS or update.effective_user.id in ALLOWED_USERS


async def my_id(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")


def make_translator():
    choice = os.getenv("TRANSLATOR") or next(
        (n for n, var in (("claude", "ANTHROPIC_API_KEY"), ("gemini", "GEMINI_API_KEY")) if os.getenv(var)),
        "google")
    if choice == "claude":
        return ClaudeTranslator(os.environ["ANTHROPIC_API_KEY"],
                                os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"))
    if choice == "gemini":
        return GeminiTranslator(os.environ["GEMINI_API_KEY"],
                                os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    return GoogleTranslator(os.environ["GOOGLE_API_KEY"])


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not permitted(update):
        return await update.message.reply_text("این بات خصوصیه. / This bot is private.")
    await update.message.reply_text(
        "سلام! فایل زیرنویس (.srt یا .vtt) رو برام بفرست، زبان مقصد رو انتخاب کن و "
        "ترجمه‌شده تحویل بگیر.\n\nSend me a subtitle file (.srt / .vtt) and pick a language.")


async def on_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not permitted(update):
        return await update.message.reply_text("این بات خصوصیه. / This bot is private.")
    doc = update.message.document
    if PurePath(doc.file_name or "").suffix.lower() not in ALLOWED:
        return await update.message.reply_text("فقط فایل‌های .srt و .vtt پشتیبانی می‌شن.")
    if doc.file_size > MAX_BYTES:
        return await update.message.reply_text("فایل بزرگ‌تر از ۵ مگابایته.")
    data = bytes(await (await doc.get_file()).download_as_bytearray())
    ctx.user_data["pending"] = (doc.file_name, data)
    langs = list(LANGUAGES.items())
    rows = [[InlineKeyboardButton(n, callback_data=f"lang:{c}") for c, n in langs[i:i + 3]]
            for i in range(0, len(langs), 3)]
    await update.message.reply_text("به چه زبانی ترجمه کنم؟ / Target language?",
                                    reply_markup=InlineKeyboardMarkup(rows))


async def on_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not permitted(update):
        return
    pending = ctx.user_data.pop("pending", None)
    if not pending:
        return await q.edit_message_text("فایل منقضی شده، دوباره بفرست.")
    name, data = pending
    target = q.data.split(":", 1)[1]
    await q.edit_message_text(f"در حال ترجمه به {LANGUAGES[target]} …")

    blocks = subtitles.parse(subtitles.decode(data))
    texts = subtitles.cue_texts(blocks)
    last = 0.0

    async def progress(done: int, total: int):
        nonlocal last
        if time.monotonic() - last > 3:  # stay under Telegram edit rate limits
            last = time.monotonic()
            await q.edit_message_text(f"در حال ترجمه به {LANGUAGES[target]} … {done}/{total}")

    try:
        translated = await translate_all(ctx.application.bot_data["translator"], texts, target,
                                         on_progress=progress)
    except Exception:
        logging.exception("translation failed")
        return await q.edit_message_text("ترجمه با خطا مواجه شد. بعداً دوباره امتحان کن.")

    out = subtitles.render(blocks, translated).encode("utf-8-sig")
    p = PurePath(name)
    await q.message.reply_document(out, filename=f"{p.stem}.{target}{p.suffix}")
    await q.edit_message_text("✅ آماده شد.")


def main():
    app = (Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"])
           .connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)
           .build())  # defaults (5s) are too short for a cold-started container
    app.bot_data["translator"] = make_translator()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(MessageHandler(filters.Document.ALL, on_file))
    app.add_handler(CallbackQueryHandler(on_language, pattern=r"^lang:"))
    # Webhook mode (e.g. Render free web service: Telegram wakes the sleeping service);
    # otherwise long polling.
    base = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if base:
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        path = hashlib.sha256(token.encode()).hexdigest()[:32]  # keeps the token out of the URL
        app.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", "8080")), url_path=path,
                        webhook_url=f"{base.rstrip('/')}/{path}", secret_token=path[::-1],
                        drop_pending_updates=True)
    else:
        app.run_polling()


if __name__ == "__main__":
    main()
