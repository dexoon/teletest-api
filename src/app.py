import os
import asyncio
import logging
from typing import List, Optional, AsyncGenerator
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends
from telethon import TelegramClient, events # Import events
from telethon.sessions import StringSession
from telethon import types

from .models import (
    SendMessageRequest,
    BotResponse,
    PressButtonRequest,
    GetMessagesResponse,
    MessageButton,
    TelegramCredentialsRequest,
    ResponseType,
)

load_dotenv()  # Load environment variables from .env file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default credentials from environment variables
DEFAULT_API_ID = os.getenv("API_ID")
DEFAULT_API_HASH = os.getenv("API_HASH")
DEFAULT_SESSION = os.getenv("SESSION_STRING")

if not all([DEFAULT_API_ID, DEFAULT_API_HASH, DEFAULT_SESSION]):
    raise RuntimeError("Default API_ID, API_HASH, and SESSION_STRING must be set in environment variables")

# Global client instance, initialized as None. Will be set up in the lifespan manager.
client: Optional[TelegramClient] = None
# app will be defined after the lifespan manager

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    global client # We are modifying the global client variable
    logger.info("Lifespan startup")
    # Startup logic
    # Fetch current environment variables for client setup.
    current_api_id = os.getenv("API_ID")
    current_api_hash = os.getenv("API_HASH")
    current_session_string = os.getenv("SESSION_STRING")
    logger.debug(
        "Credentials presence - API_ID: %s, API_HASH: %s, SESSION_STRING: %s",
        bool(current_api_id),
        bool(current_api_hash),
        bool(current_session_string),
    )

    if not all([current_api_id, current_api_hash, current_session_string]):
        raise RuntimeError(
            "Lifespan Startup Error: API_ID, API_HASH, and SESSION_STRING must be set in environment for client startup."
        )

    if client is None: # Ensure client is initialized
        if current_session_string is None:
            raise RuntimeError("Lifespan Startup Error: SESSION_STRING must be set in environment for client startup.")
        if current_api_id is None or current_api_hash is None:
            raise RuntimeError("Lifespan Startup Error: API_ID and API_HASH must be set in environment for client startup.")

        loop = asyncio.get_running_loop()
        client = TelegramClient(
            StringSession(current_session_string),
            int(current_api_id),
            current_api_hash,
            loop=loop
        )
        logger.debug("Telegram client initialized")
    
    if not client.is_connected():
        logger.debug("Starting Telegram client connection")
        await client.start()
    
    yield # Application runs here
    logger.info("Lifespan shutdown")

    # Shutdown logic
    if client and client.is_connected():
        logger.debug("Disconnecting Telegram client")
        client.disconnect()
    # client = None # Optionally reset client

app = FastAPI(title="Telegram Bot Test API", lifespan=lifespan)


@asynccontextmanager
async def get_telegram_client(
    custom_api_id: Optional[int] = None,
    custom_api_hash: Optional[str] = None,
    custom_session_string: Optional[str] = None,
) -> AsyncGenerator[TelegramClient, None]:
    global client # Ensure we're referring to the module-level client
    logger.debug("get_telegram_client called with custom creds: %s", bool(custom_session_string))
    if custom_api_id is not None and custom_api_hash and custom_session_string:
        # All custom credentials provided, create a new temporary client
        logger.debug("Creating temporary Telegram client")
        loop = asyncio.get_running_loop()
        temp_client = TelegramClient(
            StringSession(custom_session_string),
            int(custom_api_id),
            custom_api_hash,
            loop=loop
        )
        temp_client.start()
        try:
            yield temp_client
        finally:
            logger.debug("Disconnecting temporary client")
            temp_client.disconnect()
    else:
        # Use the global client
        if client is None:
            # This should not happen if startup_event ran correctly.
            raise RuntimeError("Global Telegram client has not been initialized. Check application startup logic.")

        if not client.is_connected():
            # This is a fallback/defensive measure. Startup should handle connection.
            logger.warning("Global client not connected in get_telegram_client; starting now")
            client.start()
        yield client
        # Global client's lifecycle is managed by startup/shutdown events, now via lifespan manager


# Old event handlers are removed as their logic is now in the lifespan manager.

async def get_header_credentials(
    api_id: Optional[int] = Header(None, alias="X-Telegram-Api-Id"),
    api_hash: Optional[str] = Header(None, alias="X-Telegram-Api-Hash"),
    session_string: Optional[str] = Header(None, alias="X-Telegram-Session-String"),
) -> TelegramCredentialsRequest:
    """Extract optional Telegram credentials from request headers."""
    return TelegramCredentialsRequest(api_id=api_id, api_hash=api_hash, session_string=session_string)

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


@app.post("/send-message", response_model=List[BotResponse])
async def send_message(
    req: SendMessageRequest,
    creds: TelegramCredentialsRequest = Depends(get_header_credentials),
) -> List[BotResponse]:
    logger.info("send_message called for %s", req.bot_username)
    api_id = creds.api_id
    api_hash = creds.api_hash
    session_string = creds.session_string
    
    bot_responses: List[BotResponse] = []

    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(req.bot_username)
        try:
            async with current_client.conversation(entity, timeout=req.timeout_sec) as conv:
                await conv.send_message(req.message_text)
                # Loop to collect responses
                while True:
                    try:
                        # Use a short timeout for each attempt to get a response.
                        # This allows the loop to iterate or exit if no immediate message,
                        # while the overall operation is bounded by req.timeout_sec.
                        response = await conv.get_response(timeout=0.2) # Poll for 0.2 seconds
                        logger.debug("Received response %s", response.raw_text)
                        bot_responses.append(BotResponse(
                            response_type=ResponseType.MESSAGE,
                            message_id=response.id,
                            message_text=response.raw_text,
                            reply_markup=_parse_buttons(response),
                        ))
                    except asyncio.TimeoutError:
                        # This timeout means conv.get_response(timeout=1.0) found no message in 1s.
                        # Break from this inner loop.
                        logger.debug("No more responses from bot")
                        break
        except asyncio.TimeoutError:
            # This timeout is for the entire conversation (req.timeout_sec).
            # Return whatever has been collected so far.
            logger.warning("Conversation with %s timed out", req.bot_username)
            return bot_responses
        
    return bot_responses


@app.post("/press-button", response_model=List[BotResponse])
async def press_button(
    req: PressButtonRequest,
    creds: TelegramCredentialsRequest = Depends(get_header_credentials),
) -> List[BotResponse]:
    logger.info("press_button called for %s", req.bot_username)
    if not req.button_text and not req.callback_data:
        raise HTTPException(status_code=400, detail="button_text or callback_data required")

    api_id = creds.api_id
    api_hash = creds.api_hash
    session_string = creds.session_string
    
    bot_responses: List[BotResponse] = []

    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(req.bot_username)
        
        # Get the latest message to click its button.
        messages = await current_client.get_messages(entity, limit=1)
        if not messages:
            raise HTTPException(status_code=404, detail="No messages to interact with")
        message_to_click = messages[0]
        logger.debug("Clicking button on message %s", message_to_click.id)

        try:
            async with current_client.conversation(entity, timeout=req.timeout_sec) as conv:
                try:
                    # Click the button on the fetched message
                    # message_to_click is bound to current_client which is used for the conversation
                    await message_to_click.click(text=req.button_text, data=req.callback_data)
                except Exception as e: 
                    raise HTTPException(status_code=400, detail=f"Failed to press button: {e}") from e
                
                # Loop to collect responses after clicking
                while True:
                    try:
                        # response_event is the message object for NewMessage
                        response_event = await conv.wait_event(
                            events.NewMessage(incoming=True, from_users=entity, chats=entity),
                            timeout=0.2 # Poll for 0.2 seconds
                        )
                        logger.debug("Received event message %s", response_event.raw_text)
                        bot_responses.append(BotResponse(
                            response_type=ResponseType.MESSAGE,
                            message_id=response_event.id,
                            message_text=response_event.raw_text,
                            reply_markup=_parse_buttons(response_event),
                        ))
                    except asyncio.TimeoutError:
                        # No new message event within the internal poll timeout (1s).
                        # Break from this inner loop.
                        logger.debug("No further events from bot")
                        break
        except asyncio.TimeoutError:
            # Conversation timeout (req.timeout_sec).
            # Return whatever has been collected so far.
            logger.warning("Conversation with %s timed out during press_button", req.bot_username)
            return bot_responses
            
    return bot_responses


@app.get("/get-messages", response_model=GetMessagesResponse)
async def get_messages(
    bot_username: str,
    limit: int = 5,
    creds: TelegramCredentialsRequest = Depends(get_header_credentials),
) -> GetMessagesResponse:
    logger.info("get_messages called for %s", bot_username)
    api_id = creds.api_id
    api_hash = creds.api_hash
    session_string = creds.session_string
    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(bot_username)
        messages = await current_client.get_messages(entity, limit=limit)
        logger.debug("Fetched %d messages", len(messages))
        msgs: List[BotResponse] = []
        for m in reversed(messages):
            msgs.append(BotResponse(response_type=ResponseType.MESSAGE, message_id=m.id, message_text=m.raw_text, reply_markup=_parse_buttons(m)))
    return GetMessagesResponse(messages=msgs)


@app.get("/get-updates", response_model=GetMessagesResponse)
async def get_updates(
    bot_username: str,
    limit: int = 10, # Default limit for updates
    creds: TelegramCredentialsRequest = Depends(get_header_credentials),
) -> GetMessagesResponse:
    logger.info("get_updates called for %s", bot_username)
    api_id = creds.api_id
    api_hash = creds.api_hash
    session_string = creds.session_string
    async with get_telegram_client(api_id, api_hash, session_string) as current_client:
        entity = await current_client.get_input_entity(bot_username)
        # Fetch messages, newest first
        raw_messages = await current_client.get_messages(entity, limit=limit)
        logger.debug("Fetched %d updates", len(raw_messages))
        
        processed_messages: List[BotResponse] = []
        if raw_messages:
            # Reverse to get chronological order (oldest of the batch first)
            for m in reversed(raw_messages):
                processed_messages.append(BotResponse(
                    response_type=ResponseType.MESSAGE,
                    message_id=m.id,
                    message_text=m.raw_text,
                    reply_markup=_parse_buttons(m)
                ))
    return GetMessagesResponse(messages=processed_messages)
