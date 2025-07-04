import os
import asyncio
from aiogram import Bot

async def main():
    bot_token = os.getenv("TEST_BOT_TOKEN")
    if not bot_token:
        print("Error: TEST_BOT_TOKEN not set in environment.")
        return

    bot = Bot(token=bot_token)
    try:
        me = await bot.get_me()
        if me.username:
            print(me.username)
        else:
            print("Error: Bot username is not set or could not be fetched.")
    except Exception as e:
        print(f"Error fetching bot username: {e}")
    finally:
        # Important to close the session, otherwise script might hang or cause issues in container
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
