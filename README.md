# teletest-api

A small FastAPI service for testing Telegram bots with a real user account via Telethon.

## Usage

Set the following environment variables with credentials from your Telegram test account:

- `TELEGRAM_API_ID` – your API ID
- `TELEGRAM_API_HASH` – your API hash
- `TELEGRAM_SESSION_STRING` – session string for the account

Then run the service:

```bash
python -m teletest_api
```

The service exposes a few endpoints to interact with bots:

- `POST /send-message` – send a text message to a bot and wait for a reply
- `POST /press-button` – press an inline or reply keyboard button
- `GET /get-messages` – fetch recent messages from the chat with the bot
- `POST /reset-chat` – clear dialog history with the bot

## Running tests with a real bot

The test suite can interact with a live Telegram bot if you provide the required credentials:

- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` and `TELEGRAM_SESSION_STRING` for the user account
- `TELEGRAM_BOT_TOKEN` for the bot to respond to commands
- set `RUN_REAL_BOT_TESTS=1` to enable the real bot tests

Running the tests will start the simple bot defined in `tests/real_bot.py` and exercise the API against it.
