# teletest-api

A small FastAPI service for testing Telegram bots with a real user account via Telethon.

## Usage

1.  **Set up environment variables:**
    You can set the following environment variables directly in your shell, or create a `.env` file in the project root.
    An example `.env.example` file is provided. Copy it to `.env` and fill in your credentials:
    ```bash
    cp .env.example .env
    # Now edit .env with your credentials
    ```

    Required variables:

- `API_ID` – your API ID
- `API_HASH` – your API hash
- `SESSION_STRING` – session string for the account

To obtain the session string you can run the helper script:

```bash
python generate_session.py
```
Follow the prompts to log in and the script will output the string to use. Add this string to your `.env` file or set it as an environment variable.

2.  **Run the service:**

```bash
python main.py
```

Alternatively you can run the service with Docker:

```bash
docker build -t teletest-api .
docker run -p 8000:8000 \
  -e API_ID=... \
  -e API_HASH=... \
  -e SESSION_STRING=... \
  teletest-api
```

Docker images are automatically published to
GitHub Container Registry. You can pull the latest image with:

```bash
docker pull ghcr.io/dexoon/teletest-api:latest
```

The service exposes a few endpoints to interact with bots:

- `POST /send-message` – send a text message to a bot and wait for a reply
- `POST /press-button` – press an inline or reply keyboard button
- `GET /get-messages` – fetch recent messages from the chat with the bot
- `POST /reset-chat` – clear dialog history with the bot

Custom Telegram credentials can be provided via HTTP headers:

- `X-Telegram-Api-Id`
- `X-Telegram-Api-Hash`
- `X-Telegram-Session-String`

## Running tests with a real bot

The test suite can interact with a live Telegram bot if you provide the required credentials:

- `API_ID`, `API_HASH` and `SESSION_STRING` for the user account
- `TEST_BOT_TOKEN` for the bot to respond to commands
- set `RUN_REAL_BOT_TESTS=1` to enable the real bot tests

Running the tests will start the simple bot defined in `tests/real_bot.py` and exercise the API against it.
