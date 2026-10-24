"""Telegram bot: send a subtitle file (.srt/.vtt), pick a language, get it back translated."""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import PurePath

from telegram import (BotCommand, BotCommandScopeChat, InlineKeyboardButton,
                      InlineKeyboardMarkup, Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, PersistenceInput, PicklePersistence, filters)

import subtitles
from i18n import (COMMANDS, DEFAULT_UI, DESCRIPTION, NATIVE, PICK_UI, SHORT_DESCRIPTION,
                  UI_LANGUAGES, text)
from translators import (LANGUAGES, ClaudeTranslator, GeminiTranslator, GoogleTranslator,
                         translate_all)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines contain the bot token URL
MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {".srt", ".vtt"}
# Comma-separated Telegram user IDs; empty = anyone (anyone can spend your API credit).
# Max files a user may translate per UTC day (0 = unlimited).
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))
ALLOWED_USERS = {int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip()}


def permitted(update: Update) -> bool:
    return not ALLOWED_USERS or update.effective_user.id in ALLOWED_USERS


def quota(user_data: dict) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    q = user_data.get("quota")
    if not q or q["day"] != today:
        q = user_data["quota"] = {"day": today, "used": 0}
    return q


def over_limit(user_data: dict) -> bool:
    return DAILY_LIMIT > 0 and quota(user_data)["used"] >= DAILY_LIMIT


def t(ctx: ContextTypes.DEFAULT_TYPE, key: str, **kw) -> str:
    return text(ctx.user_data.get("ui", DEFAULT_UI), key, **kw)


def commands(ui: str) -> list[BotCommand]:
    return [BotCommand(c, text(ui, f"cmd_{c}")) for c in COMMANDS]


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


def grid(buttons: list[InlineKeyboardButton], per_row: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([buttons[i:i + per_row] for i in range(0, len(buttons), per_row)])


async def ask_ui_language(update: Update, _: ContextTypes.DEFAULT_TYPE):
    kb = grid([InlineKeyboardButton(n, callback_data=f"ui:{c}") for c, n in UI_LANGUAGES.items()], 2)
    await update.effective_message.reply_text(PICK_UI, reply_markup=kb)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not permitted(update):
        return await update.message.reply_text(t(ctx, "private"))
    if "ui" not in ctx.user_data:  # first visit: ask which language the bot should speak
        return await ask_ui_language(update, ctx)
    await update.message.reply_text(t(ctx, "welcome"))


async def language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not permitted(update):
        return await update.message.reply_text(t(ctx, "private"))
    await ask_ui_language(update, ctx)


async def help_(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(ctx, "help"))


async def my_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(ctx, "your_id", id=update.effective_user.id))


async def on_ui_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not permitted(update):
        return
    ui = q.data.split(":", 1)[1]
    if ui not in UI_LANGUAGES:
        return
    ctx.user_data["ui"] = ui
    await ctx.bot.set_my_commands(commands(ui), scope=BotCommandScopeChat(q.message.chat_id))
    await q.edit_message_text(f"{t(ctx, 'ui_set')}\n\n{t(ctx, 'welcome')}")


async def on_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not permitted(update):
        return await update.message.reply_text(t(ctx, "private"))
    doc = update.message.document
    if PurePath(doc.file_name or "").suffix.lower() not in ALLOWED:
        return await update.message.reply_text(t(ctx, "bad_type"))
    if doc.file_size > MAX_BYTES:
        return await update.message.reply_text(t(ctx, "too_big"))
    if over_limit(ctx.user_data):
        return await update.message.reply_text(t(ctx, "limit_reached", limit=DAILY_LIMIT))
    data = bytes(await (await doc.get_file()).download_as_bytearray())
    # Kept in bot_data (not persisted) so uploaded files never end up in the pickle file.
    ctx.application.bot_data.setdefault("pending", {})[update.effective_user.id] = (doc.file_name, data)
    kb = grid([InlineKeyboardButton(NATIVE[c], callback_data=f"lang:{c}") for c in LANGUAGES], 3)
    await update.message.reply_text(t(ctx, "pick_target"), reply_markup=kb)


async def on_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not permitted(update):
        return
    pending = ctx.application.bot_data.get("pending", {}).pop(update.effective_user.id, None)
    if not pending:
        return await q.edit_message_text(t(ctx, "expired"))
    if over_limit(ctx.user_data):
        return await q.edit_message_text(t(ctx, "limit_reached", limit=DAILY_LIMIT))
    quota(ctx.user_data)["used"] += 1  # reserve before translating so parallel uploads can't dodge the limit
    name, data = pending
    target = q.data.split(":", 1)[1]
    lang = NATIVE[target]
    await q.edit_message_text(t(ctx, "translating", lang=lang))

    blocks = subtitles.parse(subtitles.decode(data))
    texts = subtitles.cue_texts(blocks)
    last = 0.0

    async def progress(done: int, total: int):
        nonlocal last
        if time.monotonic() - last > 3:  # stay under Telegram edit rate limits
            last = time.monotonic()
            await q.edit_message_text(t(ctx, "progress", lang=lang, done=done, total=total))

    try:
        translated = await translate_all(ctx.application.bot_data["translator"], texts, target,
                                         on_progress=progress)
    except Exception:
        logging.exception("translation failed")
        quota(ctx.user_data)["used"] -= 1  # a failed translation doesn't count
        return await q.edit_message_text(t(ctx, "failed"))

    out = subtitles.render(blocks, translated).encode("utf-8-sig")
    p = PurePath(name)
    await q.message.reply_document(out, filename=f"{p.stem}.{target}{p.suffix}")
    await q.edit_message_text(t(ctx, "done"))


async def post_init(app: Application):
    await app.bot.set_my_commands(commands(DEFAULT_UI))  # default menu is English
    await app.bot.set_my_description(DESCRIPTION)
    await app.bot.set_my_short_description(SHORT_DESCRIPTION)


def main():
    persistence = PicklePersistence(
        "state.pickle", store_data=PersistenceInput(bot_data=False, chat_data=False,
                                                    callback_data=False))
    app = (Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"])
           .persistence(persistence).post_init(post_init)
           .connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)
           .build())  # defaults (5s) are too short for a cold-started container
    app.bot_data["translator"] = make_translator()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language))
    app.add_handler(CommandHandler("help", help_))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(MessageHandler(filters.Document.ALL, on_file))
    app.add_handler(CallbackQueryHandler(on_ui_language, pattern=r"^ui:"))
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
