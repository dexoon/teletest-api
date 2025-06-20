import importlib
import os
import sys
import time
import subprocess
import signal

import pytest
from fastapi.testclient import TestClient

from pathlib import Path


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    # Ensure we have the required environment variables for real bot tests
    required_vars = ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION_STRING", "TELEGRAM_BOT_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(f"Missing required environment variables for real bot tests: {missing_vars}")
    
    import src.app as app_module
    importlib.reload(app_module)
    yield app_module


def create_client(app_module):
    return TestClient(app_module.app)


def test_ping(app, real_bot_container):
    client = TestClient(app.app)
    resp = client.post(
        "/send-message",
        json={"bot_username": "testbot", "message_text": "/ping"},
    )
    assert resp.status_code == 200
    assert resp.json()["message_text"] == "pong"


def test_buttons_and_press(app, real_bot_container):
    client = TestClient(app.app)
    # send command that returns buttons
    resp = client.post(
        "/send-message",
        json={"bot_username": "testbot", "message_text": "/buttons"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply_markup"]
    assert data["reply_markup"][0][0]["text"] == "A"

    # press button A
    resp2 = client.post(
        "/press-button",
        json={"bot_username": "testbot", "button_text": "A"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["message_text"] == "You chose A"


def test_get_and_reset_messages(app, real_bot_container):
    client = TestClient(app.app)
    client.post(
        "/send-message",
        json={"bot_username": "testbot", "message_text": "/ping"},
    )
    resp = client.get("/get-messages", params={"bot_username": "testbot", "limit": 1})
    assert resp.status_code == 200
    msgs = resp.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["message_text"] == "pong"

    # reset chat
    reset = client.post("/reset-chat", json={"bot_username": "testbot"})
    assert reset.status_code == 200
    resp2 = client.get("/get-messages", params={"bot_username": "testbot", "limit": 1})
    assert resp2.json()["messages"] == []
