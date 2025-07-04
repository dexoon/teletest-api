from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import requests

@dataclass
class TelegramCredentialsRequest:
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    session_string: Optional[str] = None


def _build_headers(creds: Optional[TelegramCredentialsRequest]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if not creds:
        return headers
    if creds.api_id is not None:
        headers["X-Telegram-Api-Id"] = str(creds.api_id)
    if creds.api_hash is not None:
        headers["X-Telegram-Api-Hash"] = creds.api_hash
    if creds.session_string is not None:
        headers["X-Telegram-Session-String"] = creds.session_string
    return headers


@dataclass
class MessageButton:
    text: str
    callback_data: Optional[str] = None


@dataclass
class BotResponse:
    message_text: str
    reply_markup: Optional[List[List[MessageButton]]] = None


@dataclass
class SendMessageRequest:
    bot_username: str
    message_text: str
    timeout_sec: Optional[int] = None


@dataclass
class PressButtonRequest:
    bot_username: str
    button_text: Optional[str] = None
    callback_data: Optional[str] = None
    timeout_sec: Optional[int] = None


@dataclass
class GetMessagesResponse:
    messages: List[BotResponse]


class TeletestApiClient:
    """Simple synchronous client for teletest-api."""

    def __init__(self, base_url: str, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def _post(self, path: str, json: Dict[str, Any], creds: Optional[TelegramCredentialsRequest]) -> Dict[str, Any]:
        resp = self.session.post(f"{self.base_url}{path}", json=json, headers=_build_headers(creds))
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: Dict[str, Any], creds: Optional[TelegramCredentialsRequest]) -> Dict[str, Any]:
        resp = self.session.get(f"{self.base_url}{path}", params=params, headers=_build_headers(creds))
        resp.raise_for_status()
        return resp.json()

    def send_message(self, req: SendMessageRequest, creds: Optional[TelegramCredentialsRequest] = None) -> BotResponse:
        data = {k: v for k, v in req.__dict__.items() if v is not None}
        resp = self._post("/send-message", data, creds)
        return BotResponse(
            message_text=resp["message_text"],
            reply_markup=[
                [MessageButton(**btn) for btn in row] for row in resp.get("reply_markup", [])
            ] if resp.get("reply_markup") else None,
        )

    def press_button(self, req: PressButtonRequest, creds: Optional[TelegramCredentialsRequest] = None) -> BotResponse:
        data = {k: v for k, v in req.__dict__.items() if v is not None}
        resp = self._post("/press-button", data, creds)
        return BotResponse(
            message_text=resp["message_text"],
            reply_markup=[
                [MessageButton(**btn) for btn in row] for row in resp.get("reply_markup", [])
            ] if resp.get("reply_markup") else None,
        )

    def get_messages(self, bot_username: str, limit: int = 5, creds: Optional[TelegramCredentialsRequest] = None) -> GetMessagesResponse:
        resp = self._get("/get-messages", {"bot_username": bot_username, "limit": limit}, creds)
        messages = [
            BotResponse(
                message_text=m["message_text"],
                reply_markup=[
                    [MessageButton(**btn) for btn in row] for row in m.get("reply_markup", [])
                ] if m.get("reply_markup") else None,
            )
            for m in resp["messages"]
        ]
        return GetMessagesResponse(messages=messages)

