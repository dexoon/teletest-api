import os

import pytest
from fastapi.testclient import TestClient

from pathlib import Path


def test_ping(app, real_bot_container): # real_bot_container fixture is already here, no change needed for this line
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/ping"},
        )
        assert resp.status_code == 200
        assert resp.json()["message_text"] == "pong"


def test_buttons_and_press(app, real_bot_container): # real_bot_container fixture is already here, no change needed for this line
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # send command that returns buttons
        resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/buttons"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply_markup"]
        assert data["reply_markup"][0][0]["text"] == "A"

        # press button A
        resp2 = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "A"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["message_text"] == "You chose A"


def test_get_and_reset_messages(app, real_bot_container): # real_bot_container fixture is already here, no change needed for this line
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/ping"},
        )
        resp = client.get("/get-messages", params={"bot_username": bot_username, "limit": 1})
        assert resp.status_code == 200
        msgs = resp.json()["messages"]
        assert len(msgs) == 1
        assert msgs[0]["message_text"] == "pong"

        # reset chat
        reset = client.post("/reset-chat", json={"bot_username": bot_username})
        assert reset.status_code == 200
        resp2 = client.get("/get-messages", params={"bot_username": bot_username, "limit": 1})
        assert resp2.json()["messages"] == []
