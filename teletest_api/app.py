import os
import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import types

from .models import (
    SendMessageRequest,
    BotResponse,
    PressButtonRequest,
    GetMessagesResponse,
    ResetChatRequest,
    MessageButton,
)

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION = os.getenv("TELEGRAM_SESSION_STRING")

if not all([API_ID, API_HASH, SESSION]):
    raise RuntimeError("TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING must be set")

client = TelegramClient(StringSession(SESSION), int(API_ID), API_HASH)
app = FastAPI(title="Telegram Bot Test API")

@app.on_event("startup")
async def startup_event() -> None:
    await client.start()

@app.on_event("shutdown")
async def shutdown_event() -> None:
    await client.disconnect()


def _parse_buttons(message: types.Message) -> Optional[List[List[MessageButton]]]:
    if not message.buttons:
        return None
    rows: List[List[MessageButton]] = []
    for row in message.buttons:
        row_data = []
        for button in row:
            text = getattr(button, "text", "")
            data = getattr(button, "data", None)
            if isinstance(data, bytes):
                try:
                    callback_data = data.decode()
                except Exception:
                    callback_data = data.hex()
            elif data is not None:
                callback_data = str(data)
            else:
                callback_data = None
            row_data.append(MessageButton(text=text, callback_data=callback_data))
        rows.append(row_data)
    return rows


@app.post("/send-message", response_model=BotResponse)
async def send_message(req: SendMessageRequest) -> BotResponse:
    entity = await client.get_input_entity(req.bot_username)
    async with client.conversation(entity, timeout=req.timeout_sec) as conv:
        await conv.send_message(req.message_text)
        try:
            response = await conv.get_response()
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Timeout waiting for bot response")
    return BotResponse(
        message_text=response.raw_text,
        reply_markup=_parse_buttons(response),
    )


@app.post("/press-button", response_model=BotResponse)
async def press_button(req: PressButtonRequest) -> BotResponse:
    if not req.button_text and not req.callback_data:
        raise HTTPException(status_code=400, detail="button_text or callback_data required")

    entity = await client.get_input_entity(req.bot_username)
    messages = await client.get_messages(entity, limit=1)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages to interact with")
    message = messages[0]

    async with client.conversation(entity, timeout=req.timeout_sec) as conv:
        try:
            await message.click(text=req.button_text, data=req.callback_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to press button: {e}")
        try:
            response = await conv.get_response()
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Timeout waiting for bot response")

    return BotResponse(
        message_text=response.raw_text,
        reply_markup=_parse_buttons(response),
    )


@app.get("/get-messages", response_model=GetMessagesResponse)
async def get_messages(bot_username: str, limit: int = 5) -> GetMessagesResponse:
    entity = await client.get_input_entity(bot_username)
    messages = await client.get_messages(entity, limit=limit)
    msgs: List[BotResponse] = []
    for m in reversed(messages):
        msgs.append(BotResponse(message_text=m.raw_text, reply_markup=_parse_buttons(m)))
    return GetMessagesResponse(messages=msgs)


@app.post("/reset-chat")
async def reset_chat(req: ResetChatRequest) -> dict:
    entity = await client.get_input_entity(req.bot_username)
    try:
        await client.delete_dialog(entity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset chat: {e}")
    return {"status": "ok"}
