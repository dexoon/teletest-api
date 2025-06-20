import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set. This is required for the bot to run.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("pong")

@dp.message(Command("buttons"))
async def buttons(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="A", callback_data="A"),
                InlineKeyboardButton(text="B", callback_data="B"),
            ]
        ]
    )
    await message.answer("Choose:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "A")
async def choose_a(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("You chose A")

@dp.callback_query(lambda c: c.data == "B")
async def choose_b(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("You chose B")

@dp.callback_query()
async def callback_other(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer(f"You sent {callback_query.data}")

@dp.message()
async def echo(message: types.Message):
    if message.text and not message.text.startswith("/"):
        await message.answer(f"echo: {message.text}")

async def main():
    print("Real aiogram bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
