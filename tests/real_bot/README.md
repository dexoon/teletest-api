# Real Bot Docker Setup

This folder contains the Docker setup for running the Telegram bot using aiogram.

## Files

- `real_bot.py` - The main bot code
- `Dockerfile` - Dockerfile using uv for dependency management
- `Dockerfile.simple` - Simpler Dockerfile using pip and requirements.txt
- `requirements.txt` - Python dependencies
- `.dockerignore` - Files to exclude from Docker build

## Usage

### Using the main Dockerfile (with uv)

```bash
# Build the image
docker build -t real-bot .

# Run the container
docker run --env-file .env real-bot
```

### Using the simple Dockerfile (with pip)

```bash
# Build the image
docker build -f Dockerfile.simple -t real-bot-simple .

# Run the container
docker run --env-file .env real-bot-simple
```

## Environment Variables

Make sure you have a `.env` file with:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token

## Features

The bot includes:
- `/ping` command - responds with "pong"
- `/buttons` command - shows inline keyboard with A and B options
- Echo functionality for non-command messages
- Callback query handling for button interactions 