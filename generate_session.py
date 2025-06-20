from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import errors

import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID') or input('Enter API ID: '))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH') or input('Enter API Hash: ')

try:
    with TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        client.start()
        print('Your session string:\n')
        print(client.session.save())
except errors.RPCError as exc:
    print(f'Failed to generate session string: {exc}')
except Exception as exc:
    print(f'Unexpected error: {exc}')

