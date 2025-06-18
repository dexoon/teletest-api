import asyncio
from typing import List, Dict, Optional

class FakeButton:
    def __init__(self, text: str, data: Optional[str] = None):
        self.text = text
        self.data = data

class FakeMessage:
    def __init__(self, text: str, buttons: Optional[List[List[FakeButton]]] = None, client=None):
        self.raw_text = text
        self.buttons = buttons
        self._client = client

    async def click(self, *, text: Optional[str] = None, data: Optional[str] = None):
        if self._client and self._client.current_conv:
            resp = self._client.bot.press_button(text=text, data=data)
            resp._client = self._client
            self._client.current_conv.last_response = resp
            self._client.dialogs.setdefault(self._client.current_conv.entity, []).append(resp)
        await asyncio.sleep(0)

class FakeConversation:
    def __init__(self, client, entity, timeout):
        self.client = client
        self.entity = entity
        self.timeout = timeout
        self.last_response = None

    async def __aenter__(self):
        self.client.current_conv = self
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.client.current_conv = None

    async def send_message(self, text: str):
        resp = self.client.bot.handle_message(text)
        resp._client = self.client
        self.last_response = resp
        self.client.dialogs.setdefault(self.entity, []).append(resp)

    async def get_response(self):
        return self.last_response

class SimpleBot:
    def handle_message(self, text: str) -> FakeMessage:
        if text == "/start":
            return FakeMessage(
                "Hello! Use /ping or /buttons.",
                [[FakeButton("Ping", data="ping")]],
                client=None,
            )
        if text == "/ping":
            return FakeMessage("pong")
        if text == "/buttons":
            return FakeMessage(
                "Choose:",
                [[FakeButton("A"), FakeButton("B")]],
            )
        return FakeMessage(f"echo: {text}")

    def press_button(self, *, text: Optional[str] = None, data: Optional[str] = None) -> FakeMessage:
        if data == "ping" or text == "Ping":
            return FakeMessage("pong from button")
        if text in {"A", "B"}:
            return FakeMessage(f"You chose {text}")
        if data:
            return FakeMessage(f"You sent {data}")
        return FakeMessage("unknown button")

class FakeTelegramClient:
    def __init__(self, session, api_id, api_hash):
        self.bot = SimpleBot()
        self.dialogs: Dict[str, List[FakeMessage]] = {}
        self.current_conv: Optional[FakeConversation] = None
        self._connected = False

    async def start(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get_input_entity(self, username):
        return username

    def conversation(self, entity, timeout=10):
        return FakeConversation(self, entity, timeout)

    async def get_messages(self, entity, limit=1):
        return self.dialogs.get(entity, [])[-limit:]

    async def delete_dialog(self, entity):
        self.dialogs[entity] = []
