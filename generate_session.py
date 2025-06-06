from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input('Enter API ID: '))
API_HASH = input('Enter API Hash: ')

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print('Your session string:\n')
    print(client.session.save())

