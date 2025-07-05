import os
import time # Added for sleep
from typing import Optional # Added for helper type hints

from fastapi.testclient import TestClient



# Helper functions
def find_message_with_text(responses: list, text: str) -> Optional[dict]:
    """Finds the first message with matching text in a list of BotResponse dicts."""
    for r in responses:
        if r.get("response_type") == "message" and r.get("message_text") == text:
            return r
    return None

def find_message_by_id_in_get_messages(get_messages_response: dict, message_id: int) -> Optional[dict]:
    """Finds a message by its ID in the 'messages' list of a GetMessagesResponse dict."""
    for m in get_messages_response.get("messages", []):
        if m.get("message_id") == message_id:
            return m
    return None


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


def test_buttons_and_press(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # Send /buttons command
        resp_buttons = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/buttons", "timeout_sec": 5},
        )
        assert resp_buttons.status_code == 200
        buttons_responses = resp_buttons.json()
        
        choose_message = find_message_with_text(buttons_responses, "Choose:")
        assert choose_message, "Initial 'Choose:' message from /buttons not found"
        assert choose_message["reply_markup"], "Buttons not found on 'Choose:' message"
        assert choose_message["reply_markup"][0][0]["text"] == "A"
        original_message_id_for_a = choose_message["message_id"]

        # Test Pressing Button A (results in an edit)
        resp_press_a = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "A", "timeout_sec": 5},
        )
        assert resp_press_a.status_code == 200
        press_a_responses = resp_press_a.json()
        # Pressing button A edits the message, doesn't send a new one.
        # So, /press-button (which waits for NewMessage) should return an empty list.
        assert isinstance(press_a_responses, list)
        assert not any(r.get("message_text") for r in press_a_responses), \
            f"Pressing button A should not yield new messages via /press-button, got: {press_a_responses}"

        # Verify the edit by fetching updates
        time.sleep(1) # Give a moment for the edit to propagate if necessary
        updates_resp_a = client.get("/get-updates", params={"bot_username": bot_username, "limit": 5})
        assert updates_resp_a.status_code == 200
        updates_a_data = updates_resp_a.json()
        
        edited_message_a = find_message_by_id_in_get_messages(updates_a_data, original_message_id_for_a)
        assert edited_message_a, f"Original message ID {original_message_id_for_a} not found in updates after pressing A"
        assert edited_message_a["message_text"] == "You chose A and I edited the message."

        # Test Pressing Button B (results in an alert and a new message)
        # Re-send /buttons to get a fresh message to click, as the previous one was edited.
        resp_buttons_again = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/buttons", "timeout_sec": 5},
        )
        assert resp_buttons_again.status_code == 200
        button_messages_again_list = resp_buttons_again.json()
        choose_message_for_b = find_message_with_text(button_messages_again_list, "Choose:")
        assert choose_message_for_b, "Could not find 'Choose:' message when re-sending /buttons for button B test"
        # original_message_id_for_b = choose_message_for_b["message_id"] # Not strictly needed for B test assertions

        resp_press_b = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "B", "timeout_sec": 5},
        )
        assert resp_press_b.status_code == 200
        press_b_responses = resp_press_b.json()
        assert isinstance(press_b_responses, list)
        
        # Expect the new message: "Additionally, I sent a new message because you chose B."
        # The alert "B was chosen!" is not captured as a message by /press-button.
        new_message_for_b = find_message_with_text(press_b_responses, "Additionally, I sent a new message because you chose B.")
        assert new_message_for_b, "Did not find new message 'Additionally, I sent a new message because you chose B.' after pressing button B"
        assert new_message_for_b["response_type"] == "message"
        assert isinstance(new_message_for_b["message_id"], int)


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
        
        # The test bot (tests/real_bot/main.py) does NOT echo unknown commands (like /nonexistentcommand).
        # Therefore, for "/nonexistentcommand", we expect no messages from the bot.
        # The `send_message` function will return an empty list if the conversation times out
        # without the bot sending any messages.
        assert not data_list, \
            f"Expected no messages for '/nonexistentcommand' on timeout, but got: {data_list}"


def test_get_updates(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # Send a message to ensure there's something to fetch
        send_resp = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/ping"},
        )
        assert send_resp.status_code == 200
        send_data_list = send_resp.json()
        # Ensure the bot responded to /ping
        assert any(m.get("message_text") == "pong" for m in send_data_list), "Bot did not respond with 'pong' to /ping"

        # Now get updates
        updates_resp = client.get("/get-updates", params={"bot_username": bot_username, "limit": 5})
        assert updates_resp.status_code == 200
        updates_data = updates_resp.json()
        assert "messages" in updates_data
        msgs = updates_data["messages"]
        assert isinstance(msgs, list)
        assert len(msgs) > 0, "No messages returned by /get-updates"

        # Check if the "pong" message is among the recent updates
        # Messages are returned oldest first from the batch.
        # The most recent message should be the bot's "pong" or the user's "/ping".
        # Given the test bot echoes, there might be other messages.
        # We are looking for the "pong".
        found_pong = any(
            msg.get("response_type") == "message" 
            and msg.get("message_text") == "pong" 
            for msg in msgs
        )
        assert found_pong, "Did not receive 'pong' message in /get-updates response"

        # Verify chronological order (oldest of the batch first) if multiple messages are present
        if len(msgs) > 1:
            # Assuming message_id is an indicator of order.
            # This might not be strictly true across different message types or edits,
            # but for simple new messages, it generally holds.
            assert msgs[0]["message_id"] < msgs[-1]["message_id"], "Messages do not appear to be in chronological order"


def test_edit_message_command(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # Send /edit_test command
        resp_send = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/edit_test", "timeout_sec": 5},
        )
        assert resp_send.status_code == 200
        send_responses = resp_send.json()
        
        # The bot first sends "Original message, I will edit this."
        # conv.get_response() in send_message should pick this up.
        original_sent_msg = find_message_with_text(send_responses, "Original message, I will edit this.")
        assert original_sent_msg, f"Initial message from /edit_test not found in {send_responses}"
        original_message_id = original_sent_msg["message_id"]

        # The bot then edits it to "Edited message!".
        # Wait a bit for the edit to surely happen on the bot side (bot has 1s sleep).
        time.sleep(2) 

        updates_resp = client.get("/get-updates", params={"bot_username": bot_username, "limit": 5})
        assert updates_resp.status_code == 200
        updates_data = updates_resp.json()
        
        edited_message = find_message_by_id_in_get_messages(updates_data, original_message_id)
        assert edited_message, f"Message ID {original_message_id} not found in updates for /edit_test: {updates_data}"
        assert edited_message["message_text"] == "Edited message!"


def test_alert_callback(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # 1. Send /alert_test to get the message with the button
        resp_send = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/alert_test", "timeout_sec": 5},
        )
        assert resp_send.status_code == 200
        send_responses = resp_send.json()
        
        alert_msg_with_button = find_message_with_text(send_responses, "Press the button to see an alert.")
        assert alert_msg_with_button, f"Message from /alert_test with button not found in {send_responses}"
        assert alert_msg_with_button["reply_markup"], "Button not found on /alert_test message"
        assert alert_msg_with_button["reply_markup"][0][0]["text"] == "Show Alert"

        # 2. Press the "Show Alert" button
        resp_press = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "Show Alert", "timeout_sec": 5},
        )
        assert resp_press.status_code == 200
        press_responses = resp_press.json()
        
        assert isinstance(press_responses, list)
        assert not any(r.get("message_text") for r in press_responses), \
            f"Pressing 'Show Alert' should not result in new messages, got: {press_responses}"


def test_new_message_from_callback(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # 1. Send /new_message_test to get the message with the button
        resp_send = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/new_message_test", "timeout_sec": 5},
        )
        assert resp_send.status_code == 200
        send_responses = resp_send.json()

        initial_msg = find_message_with_text(send_responses, "Press the button and I will send a new message.")
        assert initial_msg, f"Message from /new_message_test with button not found in {send_responses}"
        assert initial_msg["reply_markup"], "Button not found on /new_message_test message"
        assert initial_msg["reply_markup"][0][0]["text"] == "Send New Msg"

        # 2. Press the "Send New Msg" button
        resp_press = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "Send New Msg", "timeout_sec": 5},
        )
        assert resp_press.status_code == 200
        press_responses = resp_press.json()
        
        brand_new_message = find_message_with_text(press_responses, "This is a brand new message triggered by the button.")
        assert brand_new_message, f"Did not find the new message triggered by 'Send New Msg' button in {press_responses}"
        assert brand_new_message["response_type"] == "message"
        assert isinstance(brand_new_message["message_id"], int)


def test_ack_callback(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # 1. Send /ack_test to get the message with the button
        resp_send = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/ack_test", "timeout_sec": 5},
        )
        assert resp_send.status_code == 200
        send_responses = resp_send.json()

        initial_msg = find_message_with_text(send_responses, "Press the button for a simple acknowledgement.")
        assert initial_msg, f"Message from /ack_test with button not found in {send_responses}"
        assert initial_msg["reply_markup"], "Button not found on /ack_test message"
        assert initial_msg["reply_markup"][0][0]["text"] == "Just Ack"

        # 2. Press the "Just Ack" button
        resp_press = client.post(
            "/press-button",
            json={"bot_username": bot_username, "button_text": "Just Ack", "timeout_sec": 5},
        )
        assert resp_press.status_code == 200
        press_responses = resp_press.json()
        
        assert isinstance(press_responses, list)
        assert not any(r.get("message_text") for r in press_responses), \
            f"Pressing 'Just Ack' should not result in new messages, got: {press_responses}"

def test_delay_test(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # 1. Send /delay_test to get the message with the button
        resp_send = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/delay_test", "timeout_sec": 5},
        )
        assert resp_send.status_code == 200
        send_responses = resp_send.json()

        assert len(send_responses) == 2, f"Expected 2 messages from /delay_test, got: {send_responses}"
        assert send_responses[0]["message_text"] == "Waiting for 3 seconds..."
        assert send_responses[1]["message_text"] == "Done waiting!"


def test_reply_keyboard(app, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"
    with TestClient(app) as client:
        # Send command to show reply keyboard
        resp_show = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/reply_kb", "timeout_sec": 5},
        )
        assert resp_show.status_code == 200
        show_responses = resp_show.json()

        choose_msg = find_message_with_text(show_responses, "Choose an option:")
        assert choose_msg, f"Did not find reply keyboard message in {show_responses}"
        assert choose_msg["reply_markup"], "Reply keyboard not present on message"
        assert choose_msg["reply_keyboard"] is True
        assert choose_msg["reply_markup"][0][0]["text"] == "Option 1"

        # Select first option using send_message
        resp_press = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "Option 1", "timeout_sec": 5},
        )
        assert resp_press.status_code == 200
        press_responses = resp_press.json()
        selected = find_message_with_text(press_responses, "You chose option 1")
        assert selected, f"Response to reply keyboard selection not found in {press_responses}"
        assert selected["reply_keyboard"] is False

        # Remove keyboard to not interfere with other tests
        resp_remove = client.post(
            "/send-message",
            json={"bot_username": bot_username, "message_text": "/remove_kb", "timeout_sec": 5},
        )
        assert resp_remove.status_code == 200
        remove_responses = resp_remove.json()
        remove_msg = find_message_with_text(remove_responses, "Keyboard removed")
        assert remove_msg, f"Remove keyboard response not found in {remove_responses}"
