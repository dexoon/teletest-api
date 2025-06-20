from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import errors

import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID') or input('Enter API ID: '))
API_HASH = os.getenv('API_HASH') or input('Enter API Hash: ')

try:
    with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        client.start()
        print('Your session string:\n')
        print(client.session.save())
except errors.RPCError as exc:
    print(f'Failed to generate session string: {exc}')
except Exception as exc:
    print(f'Unexpected error: {exc}')

