# Sub-translate

Telegram bot: send a `.srt` / `.vtt` file, pick a language, get it back translated.
Translators: Claude (default, best for dialogue) or Google Cloud Translation.

## Run locally
    pip install -r requirements.txt
    cp .env.example .env   # fill in, then export the variables
    python bot.py

## Deploy on Fly.io
    fly auth login
    fly launch --no-deploy --copy-config      # pick a unique app name; say NO to databases
    fly secrets set TELEGRAM_BOT_TOKEN=... ANTHROPIC_API_KEY=... ALLOWED_USERS=<your id>
    fly deploy --ha=false                     # exactly one machine (two would both poll Telegram)
    fly logs

Send `/id` to the bot to learn your Telegram ID for `ALLOWED_USERS`.
To use Google instead: `fly secrets set TRANSLATOR=google GOOGLE_API_KEY=...`.
