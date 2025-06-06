import importlib
import os
import sys
import time
import subprocess

import pytest
from fastapi.testclient import TestClient

from pathlib import Path

from .fake_telegram import FakeTelegramClient


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    use_real = os.getenv("RUN_REAL_BOT_TESTS")
    if not use_real:
        monkeypatch.setenv("TELEGRAM_API_ID", "1")
        monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
        monkeypatch.setenv("TELEGRAM_SESSION_STRING", "session")
        monkeypatch.setattr("telethon.TelegramClient", FakeTelegramClient)
        monkeypatch.setattr("telethon.sessions.StringSession", lambda s: s)
    import teletest_api.app as app_module

    importlib.reload(app_module)
    yield app_module


@pytest.fixture(scope="module")
def bot_process():
    if not os.getenv("RUN_REAL_BOT_TESTS"):
        yield
        return
    script = Path(__file__).with_name("real_bot.py")
    env = os.environ.copy()
    proc = subprocess.Popen([sys.executable, str(script)], env=env)
    time.sleep(3)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def create_client(app_module):
    return TestClient(app_module.app)


def test_ping(setup_env, bot_process):
    client = create_client(setup_env)
    resp = client.post(
        "/send-message",
        json={"bot_username": "testbot", "message_text": "/ping"},
    )
    assert resp.status_code == 200
    assert resp.json()["message_text"] == "pong"


def test_buttons_and_press(setup_env, bot_process):
    client = create_client(setup_env)
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


def test_get_and_reset_messages(setup_env, bot_process):
    client = create_client(setup_env)
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
