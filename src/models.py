from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class ResponseType(str, Enum):
    MESSAGE = "message"
    EDITED_MESSAGE = "edited_message"
    CALLBACK_ANSWER = "callback_answer"
    POPUP = "popup"

class TelegramCredentialsRequest(BaseModel):
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    session_string: Optional[str] = None

class MessageButton(BaseModel):
    text: str
    callback_data: Optional[str] = None

class BotResponse(BaseModel):
    response_type: ResponseType
    message_text: Optional[str] = None  # For MESSAGE, EDITED_MESSAGE
    reply_markup: Optional[List[List[MessageButton]]] = None # For MESSAGE, EDITED_MESSAGE
    
    # For CALLBACK_ANSWER
    callback_answer_text: Optional[str] = None
    callback_answer_alert: Optional[bool] = None

    # For POPUP
    popup_message: Optional[str] = None

class SendMessageRequest(BaseModel):
    bot_username: str
    message_text: str
    timeout_sec: int = 10

class PressButtonRequest(BaseModel):
    bot_username: str
    button_text: Optional[str] = None
    callback_data: Optional[str] = None
    timeout_sec: int = 10

class GetMessagesResponse(BaseModel):
    messages: List[BotResponse]
