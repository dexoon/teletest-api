import os
import asyncio
from telethon import TelegramClient, events, Button

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

client = TelegramClient("real_bot", API_ID, API_HASH)


@client.on(events.NewMessage(pattern="/ping"))
async def ping(event):
    await event.respond("pong")


@client.on(events.NewMessage(pattern="/buttons"))
async def buttons(event):
    await event.respond(
        "Choose:", buttons=[[Button.inline("A", b"A"), Button.inline("B", b"B")]]
    )


@client.on(events.CallbackQuery(data=b"A"))
async def choose_a(event):
    await event.answer()
    await event.respond("You chose A")


@client.on(events.CallbackQuery(data=b"B"))
async def choose_b(event):
    await event.answer()
    await event.respond("You chose B")


@client.on(events.CallbackQuery)
async def callback_other(event):
    await event.answer()
    await event.respond(f"You sent {event.data.decode()}")


@client.on(events.NewMessage)
async def echo(event):
    if not event.raw_text.startswith("/"):
        await event.respond(f"echo: {event.raw_text}")


async def main():
    await client.start(bot_token=BOT_TOKEN)
    print("Real bot started")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
