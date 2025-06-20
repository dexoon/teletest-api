import os

import pytest
from fastapi.testclient import TestClient

from pathlib import Path


def test_ping(app, ping_bot): # ping_bot fixture is already here, no change needed for this line
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/ping"},
        )
        assert resp.status_code == 200
        data_list = resp.json()
        assert isinstance(data_list, list)
        assert len(data_list) == 1
        data = data_list[0]
        assert data["response_type"] == "message"
        assert data["message_text"] == "pong"


def test_buttons_and_press(app, ping_bot): # ping_bot fixture is already here, no change needed for this line
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # send command that returns buttons
        resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/buttons"},
        )
        assert resp.status_code == 200
        data_list = resp.json()
        assert isinstance(data_list, list)
        assert len(data_list) == 1
        data = data_list[0]
        assert data["response_type"] == "message"
        assert data["reply_markup"]
        assert data["reply_markup"][0][0]["text"] == "A"

        # press button A
        resp2 = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "A"},
        )
        assert resp2.status_code == 200
        data_list2 = resp2.json()
        assert isinstance(data_list2, list)
        assert len(data_list2) == 1
        data2 = data_list2[0]
        assert data2["response_type"] == "message"
        assert data2["message_text"] == "You chose A"


def test_get_messages(app, ping_bot): # Renamed from test_get_and_reset_messages
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # Isolation: Fetch existing messages to clear the buffer for this test run
        # This ensures that the subsequent fetch only contains messages sent during this test.
        initial_fetch_resp = client.get("/get-messages", params={"bot_username": bot_username, "limit": 100}) # Fetch up to 100 messages
        assert initial_fetch_resp.status_code == 200
        # We don't strictly need to assert the content of initial_fetch_resp, just that the call worked.

        # Send a message to trigger a response from the bot
        ping_resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/ping"},
        )
        assert ping_resp.status_code == 200
        ping_data_list = ping_resp.json()
        assert isinstance(ping_data_list, list)
        assert len(ping_data_list) == 1
        ping_data = ping_data_list[0]
        assert ping_data["response_type"] == "message"
        assert ping_data["message_text"] == "pong" # Ensure the bot responded

        # Now get messages
        resp = client.get("/get-messages", params={"bot_username": bot_username, "limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        msgs = data["messages"]
        
        # Check that we received at least one message (the "pong" reply)
        # Depending on chat history, there might be more.
        # The important part is that the API call works and returns a list.
        assert isinstance(msgs, list)
        # Check that we received at least one message (the "pong" reply)
        assert len(msgs) >= 1
        
        # Check if any message in the list is a "pong" message response
        pong_received = any(
            msg.get("response_type") == "message" and msg.get("message_text") == "pong"
            for msg in msgs
        )
        assert pong_received, "Did not receive 'pong' message from the bot"

def test_send_message_timeout(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # Use a very short timeout to force a timeout
        # Assuming the bot won't respond to "/nonexistentcommand" or will take longer than 0.1s
        resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/nonexistentcommand", "timeout_sec": 1},
        )
        assert resp.status_code == 200
        assert resp.json() == []

def test_press_button_timeout(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # First, send a message that has buttons to ensure there's something to click
        client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/buttons"},
        )
        # Now, attempt to press a button with a very short timeout
        resp = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "A", "timeout_sec": 1},
        )
        assert resp.status_code == 200
        assert resp.json() == []
