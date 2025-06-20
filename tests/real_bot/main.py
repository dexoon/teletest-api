import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

BOT_TOKEN = os.getenv("TEST_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TEST_BOT_TOKEN environment variable is not set. This is required for the bot to run.")

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
    await callback_query.answer() # Acknowledge
    await callback_query.message.edit_text("You chose A and I edited the message.")

@dp.callback_query(lambda c: c.data == "B")
async def choose_b(callback_query: types.CallbackQuery):
    await callback_query.answer("B was chosen!", show_alert=True) # Popup
    await callback_query.message.answer("Additionally, I sent a new message because you chose B.") # New message

# Command to test message editing
@dp.message(Command("edit_test"))
async def edit_test(message: types.Message):
    sent_message = await message.answer("Original message, I will edit this.")
    await asyncio.sleep(1) # Small delay to make the edit noticeable
    await bot.edit_message_text("Edited message!", chat_id=message.chat.id, message_id=sent_message.message_id)

# Command to test popup alerts from callbacks
@dp.message(Command("alert_test"))
async def alert_test(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Show Alert", callback_data="show_alert_button")]]
    )
    await message.answer("Press the button to see an alert.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "show_alert_button")
async def handle_show_alert_button(callback_query: types.CallbackQuery):
    await callback_query.answer("This is a popup alert!", show_alert=True)

# Command to test bot sending a new message after a callback
@dp.message(Command("new_message_test"))
async def new_message_test(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Send New Msg", callback_data="send_new_message_button")]]
    )
    await message.answer("Press the button and I will send a new message.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "send_new_message_button")
async def handle_send_new_message_button(callback_query: types.CallbackQuery):
    await callback_query.answer("Acknowledged. Sending new message...") # Simple ack for the button press
    await callback_query.message.answer("This is a brand new message triggered by the button.")

# Command to test simple callback acknowledgement
@dp.message(Command("ack_test"))
async def ack_test(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Just Ack", callback_data="just_ack_button")]]
    )
    await message.answer("Press the button for a simple acknowledgement.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "just_ack_button")
async def handle_just_ack_button(callback_query: types.CallbackQuery):
    await callback_query.answer("Acknowledged!") # This text might appear as a brief notification

# Generic callback handler for unhandled callback data (must be after specific ones)
@dp.callback_query()
async def callback_other(callback_query: types.CallbackQuery):
    await callback_query.answer(f"Callback received: {callback_query.data}") # Answer without alert
    await callback_query.message.answer(f"Bot received unhandled callback data: {callback_query.data}")

# Generic message handler (must be last)
@dp.message()
async def echo(message: types.Message):
    # Check if the message text is not None and not a command
    if message.text and not message.text.startswith("/"):
        await message.answer(f"echo: {message.text}")
    # If it's a command not handled by other handlers, it will be ignored by this function.
    # Or you can add a specific message for unhandled commands:
    # elif message.text and message.text.startswith("/"):
    #     await message.answer(f"Unknown command: {message.text}")


async def main():
    print("Real aiogram bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
