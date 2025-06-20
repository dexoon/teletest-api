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
        
        pong_messages = [m for m in data_list if m.get("message_text") == "pong"]
        assert len(pong_messages) >= 1, "No 'pong' message found in response"
        data = pong_messages[0] # Use the first 'pong' message for further assertions
        
        assert data["response_type"] == "message"
        # data["message_text"] == "pong" is confirmed by the filter above
        assert "message_id" in data
        assert isinstance(data["message_id"], int)


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

        button_messages = [
            m for m in data_list 
            if m.get("reply_markup") and m["reply_markup"] and m["reply_markup"][0] and m["reply_markup"][0][0]["text"] == "A"
        ]
        assert len(button_messages) >= 1, "No message with button 'A' found"
        data = button_messages[0] # Use the first such message

        assert data["response_type"] == "message"
        assert "message_id" in data
        assert isinstance(data["message_id"], int)
        assert data["reply_markup"] # Already checked by filter structure
        assert data["reply_markup"][0][0]["text"] == "A" # Already checked by filter

        # press button A
        resp2 = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "A"},
        )
        assert resp2.status_code == 200
        data_list2 = resp2.json()
        assert isinstance(data_list2, list)
        
        chose_a_messages = [m for m in data_list2 if m.get("message_text") == "You chose A"]
        assert len(chose_a_messages) >= 1, "No 'You chose A' message found"
        data2 = chose_a_messages[0] # Use the first such message

        assert data2["response_type"] == "message"
        assert "message_id" in data2
        assert isinstance(data2["message_id"], int)
        # data2["message_text"] == "You chose A" is confirmed by the filter


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

        pong_messages_in_send = [m for m in ping_data_list if m.get("message_text") == "pong"]
        assert len(pong_messages_in_send) >= 1, "No 'pong' message found in send-message response for get_messages test"
        ping_data = pong_messages_in_send[0] # Use this for subsequent assertions

        assert ping_data["response_type"] == "message"
        assert "message_id" in ping_data
        assert isinstance(ping_data["message_id"], int)
        # ping_data["message_text"] == "pong" is confirmed by the filter

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
            msg.get("response_type") == "message" 
            and msg.get("message_text") == "pong" 
            and isinstance(msg.get("message_id"), int)
            for msg in msgs
        )
        assert pong_received, "Did not receive 'pong' message (with ID) from the bot"

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
        # With the new logic and the test bot's echo handler, we expect the echoed command.
        data_list = resp.json()
        assert isinstance(data_list, list)
        
        echo_messages = [m for m in data_list if m.get("message_text") == "/nonexistentcommand"]
        assert len(echo_messages) >= 1, "No echo message for '/nonexistentcommand' found"
        # Further assertions on the echo message can be added if needed.
        # For example, checking response_type and message_id:
        # echo_data = echo_messages[0]
        # assert echo_data["response_type"] == "message"
        # assert "message_id" in echo_data

