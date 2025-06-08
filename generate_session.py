from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import errors

API_ID = int(input('Enter API ID: '))
API_HASH = input('Enter API Hash: ')

try:
    with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        client.start()
        print('Your session string:\n')
        print(client.session.save())
except errors.RPCError as exc:
    print(f'Failed to generate session string: {exc}')
except Exception as exc:
    print(f'Unexpected error: {exc}')

