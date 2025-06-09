from pydantic import BaseModel
from typing import List, Optional

class TelegramCredentialsRequest(BaseModel):
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    session_string: Optional[str] = None

class MessageButton(BaseModel):
    text: str
    callback_data: Optional[str] = None

class BotResponse(BaseModel):
    message_text: str
    reply_markup: Optional[List[List[MessageButton]]] = None

class SendMessageRequest(BaseModel):
    bot_username: str
    message_text: str
    timeout_sec: int = 10
    credentials: Optional[TelegramCredentialsRequest] = None

class PressButtonRequest(BaseModel):
    bot_username: str
    button_text: Optional[str] = None
    callback_data: Optional[str] = None
    timeout_sec: int = 10
    credentials: Optional[TelegramCredentialsRequest] = None

class GetMessagesResponse(BaseModel):
    messages: List[BotResponse]

class ResetChatRequest(BaseModel):
    bot_username: str
    credentials: Optional[TelegramCredentialsRequest] = None
