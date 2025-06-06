# teletest-api

A small FastAPI service for testing Telegram bots with a real user account via Telethon.

## Usage

Set the following environment variables with credentials from your Telegram test account:

- `TELEGRAM_API_ID` – your API ID
- `TELEGRAM_API_HASH` – your API hash
- `TELEGRAM_SESSION_STRING` – session string for the account

To obtain the session string you can run the helper script:

```bash
python generate_session.py
```
Follow the prompts to log in and the script will output the string to use.

Then run the service:

```bash
python -m teletest_api
```

Alternatively you can run the service with Docker:

```bash
docker build -t teletest-api .
docker run -p 8000:8000 \
  -e TELEGRAM_API_ID=... \
  -e TELEGRAM_API_HASH=... \
  -e TELEGRAM_SESSION_STRING=... \
  teletest-api
```

The service exposes a few endpoints to interact with bots:

- `POST /send-message` – send a text message to a bot and wait for a reply
- `POST /press-button` – press an inline or reply keyboard button
- `GET /get-messages` – fetch recent messages from the chat with the bot
- `POST /reset-chat` – clear dialog history with the bot
