import os
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
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
    TelegramCredentialsRequest,
)

load_dotenv()  # Load environment variables from .env file

# Default credentials from environment variables
DEFAULT_API_ID = os.getenv("TELEGRAM_API_ID")
DEFAULT_API_HASH = os.getenv("TELEGRAM_API_HASH")
DEFAULT_SESSION = os.getenv("TELEGRAM_SESSION_STRING")

if not all([DEFAULT_API_ID, DEFAULT_API_HASH, DEFAULT_SESSION]):
    raise RuntimeError("Default TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_STRING must be set in environment variables")

# Global client instance, initialized as None. Will be set up in startup_event.
client: Optional[TelegramClient] = None
app = FastAPI(title="Telegram Bot Test API")


@asynccontextmanager
async def get_telegram_client(
    custom_api_id: Optional[int] = None,
    custom_api_hash: Optional[str] = None,
    custom_session_string: Optional[str] = None,
):
    global client # Ensure we're referring to the module-level client
    if custom_api_id is not None and custom_api_hash and custom_session_string:
        # All custom credentials provided, create a new temporary client
        loop = asyncio.get_running_loop()
        temp_client = TelegramClient(
            StringSession(custom_session_string),
            int(custom_api_id),
            custom_api_hash,
            loop=loop
        )
        await temp_client.start() # Make sure temp_client is started
        try:
            yield temp_client
        finally:
            await temp_client.disconnect()
    else:
        # Use the global client
        if client is None:
            # This should not happen if startup_event ran correctly.
            raise RuntimeError("Global Telegram client has not been initialized. Check application startup logic.")
        
        if not client.is_connected():
            # This is a fallback/defensive measure. Startup should handle connection.
            # Consider logging a warning here if it happens.
            # print("Warning: Global client was not connected in get_telegram_client, attempting to start.")
            await client.start()
        yield client
        # Global client's lifecycle is managed by startup/shutdown events


@app.on_event("startup")
async def startup_event() -> None:
    global client # We are modifying the global client variable

    # Fetch current environment variables for client setup.
    # These are expected to be set by the time the app starts.
    # In tests, conftest.py's load_dotenv ensures these are available from .env.test before src.app is reloaded.
    current_api_id = os.getenv("TELEGRAM_API_ID")
    current_api_hash = os.getenv("TELEGRAM_API_HASH")
    current_session_string = os.getenv("TELEGRAM_SESSION_STRING")

    # These should have been checked at module level already for defaults,
    # but good to ensure they are present for client instantiation here.
    if not all([current_api_id, current_api_hash, current_session_string]):
        raise RuntimeError(
            "Startup Error: TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_STRING must be set in environment for client startup."
        )

    # Instantiate the client if it hasn't been already
    if client is None:
        loop = asyncio.get_running_loop()
        client = TelegramClient(
            StringSession(current_session_string),
            int(current_api_id),
            current_api_hash,
            loop=loop
        )
    
    # Ensure the client is started
    if not client.is_connected():
        await client.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global client
    if client and client.is_connected():
        await client.disconnect()
    # client = None # Optionally reset client to None


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
    creds = req.credentials
    api_id = creds.api_id if creds else None
    api_hash = creds.api_hash if creds else None
    session_string = creds.session_string if creds else None

    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(req.bot_username)
        try:
            async with current_client.conversation(entity, timeout=req.timeout_sec) as conv:
                await conv.send_message(req.message_text)
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

    creds = req.credentials
    api_id = creds.api_id if creds else None
    api_hash = creds.api_hash if creds else None
    session_string = creds.session_string if creds else None

    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(req.bot_username)
        messages = await current_client.get_messages(entity, limit=1)
        if not messages:
            raise HTTPException(status_code=404, detail="No messages to interact with")
        message = messages[0]

        # Attach the client to the message object if it's from a different client
        # This ensures message.click() uses the correct client context.
        # However, Telethon messages are typically bound to the client that fetched them.
        # Re-fetching the message with current_client might be safer if issues arise,
        # but often .click() works if the underlying message ID is valid.
        # For now, let's assume direct .click() is okay. If not, one would re-fetch:
        # message = await current_client.get_messages(entity, ids=message.id)

        try:
            async with current_client.conversation(entity, timeout=req.timeout_sec) as conv:
                try:
                    # Ensure the message object uses the current client for its operations
                    # One way is to ensure methods like message.click() are called on a message
                    # that is aware of 'current_client', or that client is passed if API allows.
                    # Telethon's message.click() uses the client instance that the message object
                    # was created with. If current_client is a temporary one, and message was fetched
                    # by global client (or vice-versa), this could be an issue.
                    # A simple way to ensure correctness is to re-fetch the message with current_client
                    # if we are using a temporary client or if there's doubt.
                    # However, for simplicity, let's try direct click first.
                    # If issues arise, one would do:
                    # if current_client is not client: # i.e., it's a temporary client
                    #    message = await current_client.get_messages(await current_client.get_input_entity(req.bot_username), ids=message.id)

                    await message.click(text=req.button_text, data=req.callback_data)
                except Exception as e: # Catches errors specifically from message.click()
                    raise HTTPException(status_code=400, detail=f"Failed to press button: {e}")
                
                response = await conv.get_response() # Covered by the outer timeout handler
        except asyncio.TimeoutError: # Catches timeout from the conversation
            raise HTTPException(status_code=504, detail="Timeout waiting for bot response")

    return BotResponse(
        message_text=response.raw_text,
        reply_markup=_parse_buttons(response),
    )


@app.get("/get-messages", response_model=GetMessagesResponse)
async def get_messages(
    bot_username: str,
    limit: int = 5,
    api_id: Optional[int] = Query(None, description="Custom API ID"),
    api_hash: Optional[str] = Query(None, description="Custom API Hash"),
    session_string: Optional[str] = Query(None, description="Custom Session String")
) -> GetMessagesResponse:
    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(bot_username)
        messages = await current_client.get_messages(entity, limit=limit)
        msgs: List[BotResponse] = []
        for m in reversed(messages):
            msgs.append(BotResponse(message_text=m.raw_text, reply_markup=_parse_buttons(m)))
    return GetMessagesResponse(messages=msgs)


@app.post("/reset-chat")
async def reset_chat(req: ResetChatRequest) -> dict:
    creds = req.credentials
    api_id = creds.api_id if creds else None
    api_hash = creds.api_hash if creds else None
    session_string = creds.session_string if creds else None

    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(req.bot_username)
        try:
            await current_client.delete_dialog(entity)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reset chat: {e}")
    return {"status": "ok"}
