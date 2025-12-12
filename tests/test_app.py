import os
import time
from typing import Optional, List

# Import models from the client library
import sys
# Make sure we can import from clients (should be handled by conftest but just in case for static analysis/IDE)
# sys.path.append(os.path.join(os.path.dirname(__file__), "../clients/python-client"))
from teletest_api_client import (
    SendMessageRequest,
    PressButtonRequest,
    BotResponse,
    ResponseType,
)


# Helper functions adjusted for BotResponse objects
def find_message_with_text(responses: List[BotResponse], text: str) -> Optional[BotResponse]:
    """Finds the first message with matching text in a list of BotResponse objects."""
    for r in responses:
        if r.response_type == ResponseType.MESSAGE and r.message_text == text:
            return r
    return None

def find_message_by_id_in_list(messages: List[BotResponse], message_id: int) -> Optional[BotResponse]:
    """Finds a message by its ID in a list of BotResponse objects."""
    for m in messages:
        if m.message_id == message_id:
            return m
    return None


def test_ping(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/ping")
    )

    pong_message = find_message_with_text(responses, "pong")
    assert pong_message, "No 'pong' message found in response"

    assert pong_message.response_type == ResponseType.MESSAGE
    assert pong_message.message_id is not None
    assert isinstance(pong_message.message_id, int)


def test_buttons_and_press(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # Send /buttons command
    buttons_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/buttons", timeout_sec=5)
    )

    choose_message = find_message_with_text(buttons_responses, "Choose:")
    assert choose_message, "Initial 'Choose:' message from /buttons not found"
    assert choose_message.reply_markup, "Buttons not found on 'Choose:' message"
    assert choose_message.reply_markup[0][0].text == "A"
    original_message_id_for_a = choose_message.message_id

    # Test Pressing Button A (results in an edit)
    press_a_responses = teletest_client.press_button(
        PressButtonRequest(bot_username=bot_username, button_text="A", timeout_sec=5)
    )

    # Pressing button A edits the message, doesn't send a new one.
    # So, /press-button (which waits for NewMessage) should return an empty list.
    assert isinstance(press_a_responses, list)
    assert not any(r.message_text for r in press_a_responses if r.response_type == ResponseType.MESSAGE), \
        f"Pressing button A should not yield new messages via /press-button, got: {press_a_responses}"

    # Verify the edit by fetching updates
    time.sleep(1) # Give a moment for the edit to propagate if necessary
    updates_a = teletest_client.get_messages(bot_username=bot_username, limit=5)

    edited_message_a = find_message_by_id_in_list(updates_a.messages, original_message_id_for_a)
    assert edited_message_a, f"Original message ID {original_message_id_for_a} not found in updates after pressing A"
    assert edited_message_a.message_text == "You chose A and I edited the message."

    # Test Pressing Button B (results in an alert and a new message)
    # Re-send /buttons to get a fresh message to click, as the previous one was edited.
    button_messages_again_list = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/buttons", timeout_sec=5)
    )

    choose_message_for_b = find_message_with_text(button_messages_again_list, "Choose:")
    assert choose_message_for_b, "Could not find 'Choose:' message when re-sending /buttons for button B test"

    press_b_responses = teletest_client.press_button(
        PressButtonRequest(bot_username=bot_username, button_text="B", timeout_sec=5)
    )
    assert isinstance(press_b_responses, list)

    # Expect the new message: "Additionally, I sent a new message because you chose B."
    # The alert "B was chosen!" is not captured as a message by /press-button (unless it captures popup/callback_answer).
    # TeletestApiClient.press_button returns List[BotResponse]. BotResponse includes callback_answer_text/popup_message if available.

    new_message_for_b = find_message_with_text(press_b_responses, "Additionally, I sent a new message because you chose B.")
    assert new_message_for_b, "Did not find new message 'Additionally, I sent a new message because you chose B.' after pressing button B"
    assert new_message_for_b.response_type == ResponseType.MESSAGE
    assert isinstance(new_message_for_b.message_id, int)


def test_get_messages(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # Isolation: Fetch existing messages to clear the buffer for this test run
    # This ensures that the subsequent fetch only contains messages sent during this test.
    teletest_client.get_messages(bot_username=bot_username, limit=100)

    # Send a message to trigger a response from the bot
    ping_data_list = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/ping")
    )
    assert isinstance(ping_data_list, list)

    pong_message = find_message_with_text(ping_data_list, "pong")
    assert pong_message, "No 'pong' message found in send-message response for get_messages test"

    assert pong_message.response_type == ResponseType.MESSAGE
    assert pong_message.message_id is not None
    assert isinstance(pong_message.message_id, int)

    # Now get messages
    resp = teletest_client.get_messages(bot_username=bot_username, limit=1)
    msgs = resp.messages

    assert isinstance(msgs, list)
    # Check that we received at least one message (the "pong" reply)
    assert len(msgs) >= 1

    # Check if any message in the list is a "pong" message response
    pong_received = any(
        msg.response_type == ResponseType.MESSAGE
        and msg.message_text == "pong"
        and isinstance(msg.message_id, int)
        for msg in msgs
    )
    assert pong_received, "Did not receive 'pong' message (with ID) from the bot"

def test_send_message_timeout(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # Use a very short timeout to force a timeout
    # Assuming the bot won't respond to "/nonexistentcommand" or will take longer than 0.1s
    data_list = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/nonexistentcommand", timeout_sec=1)
    )

    # The test bot (tests/real_bot/main.py) does NOT echo unknown commands (like /nonexistentcommand).
    # Therefore, for "/nonexistentcommand", we expect no messages from the bot.
    # The `send_message` function will return an empty list if the conversation times out
    # without the bot sending any messages.
    assert not data_list, \
        f"Expected no messages for '/nonexistentcommand' on timeout, but got: {data_list}"


def test_get_updates(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # Send a message to ensure there's something to fetch
    send_data_list = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/ping")
    )

    # Ensure the bot responded to /ping
    assert any(m.message_text == "pong" for m in send_data_list), "Bot did not respond with 'pong' to /ping"

    # Now get updates
    updates_resp = teletest_client.get_messages(bot_username=bot_username, limit=5)
    msgs = updates_resp.messages
    assert isinstance(msgs, list)
    assert len(msgs) > 0, "No messages returned by /get-updates"

    # Check if the "pong" message is among the recent updates
    found_pong = any(
        msg.response_type == ResponseType.MESSAGE
        and msg.message_text == "pong"
        for msg in msgs
    )
    assert found_pong, "Did not receive 'pong' message in /get-updates response"

    # Verify chronological order (oldest of the batch first) if multiple messages are present
    if len(msgs) > 1:
        # Assuming message_id is an indicator of order.
        assert msgs[0].message_id < msgs[-1].message_id, "Messages do not appear to be in chronological order"


def test_edit_message_command(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # Send /edit_test command
    send_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/edit_test", timeout_sec=5)
    )

    # The bot first sends "Original message, I will edit this."
    original_sent_msg = find_message_with_text(send_responses, "Original message, I will edit this.")
    assert original_sent_msg, f"Initial message from /edit_test not found in {send_responses}"
    original_message_id = original_sent_msg.message_id

    # The bot then edits it to "Edited message!".
    # Wait a bit for the edit to surely happen on the bot side (bot has 1s sleep).
    time.sleep(2)

    updates_resp = teletest_client.get_messages(bot_username=bot_username, limit=5)
    updates_data = updates_resp.messages

    edited_message = find_message_by_id_in_list(updates_data, original_message_id)
    assert edited_message, f"Message ID {original_message_id} not found in updates for /edit_test: {updates_data}"
    assert edited_message.message_text == "Edited message!"


def test_alert_callback(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # 1. Send /alert_test to get the message with the button
    send_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/alert_test", timeout_sec=5)
    )

    alert_msg_with_button = find_message_with_text(send_responses, "Press the button to see an alert.")
    assert alert_msg_with_button, f"Message from /alert_test with button not found in {send_responses}"
    assert alert_msg_with_button.reply_markup, "Button not found on /alert_test message"
    assert alert_msg_with_button.reply_markup[0][0].text == "Show Alert"

    # 2. Press the "Show Alert" button
    press_responses = teletest_client.press_button(
        PressButtonRequest(bot_username=bot_username, button_text="Show Alert", timeout_sec=5)
    )

    assert isinstance(press_responses, list)
    assert not any(r.message_text for r in press_responses if r.response_type == ResponseType.MESSAGE), \
        f"Pressing 'Show Alert' should not result in new messages, got: {press_responses}"


def test_new_message_from_callback(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # 1. Send /new_message_test to get the message with the button
    send_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/new_message_test", timeout_sec=5)
    )

    initial_msg = find_message_with_text(send_responses, "Press the button and I will send a new message.")
    assert initial_msg, f"Message from /new_message_test with button not found in {send_responses}"
    assert initial_msg.reply_markup, "Button not found on /new_message_test message"
    assert initial_msg.reply_markup[0][0].text == "Send New Msg"

    # 2. Press the "Send New Msg" button
    press_responses = teletest_client.press_button(
        PressButtonRequest(bot_username=bot_username, button_text="Send New Msg", timeout_sec=5)
    )

    brand_new_message = find_message_with_text(press_responses, "This is a brand new message triggered by the button.")
    assert brand_new_message, f"Did not find the new message triggered by 'Send New Msg' button in {press_responses}"
    assert brand_new_message.response_type == ResponseType.MESSAGE
    assert isinstance(brand_new_message.message_id, int)


def test_ack_callback(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # 1. Send /ack_test to get the message with the button
    send_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/ack_test", timeout_sec=5)
    )

    initial_msg = find_message_with_text(send_responses, "Press the button for a simple acknowledgement.")
    assert initial_msg, f"Message from /ack_test with button not found in {send_responses}"
    assert initial_msg.reply_markup, "Button not found on /ack_test message"
    assert initial_msg.reply_markup[0][0].text == "Just Ack"

    # 2. Press the "Just Ack" button
    press_responses = teletest_client.press_button(
        PressButtonRequest(bot_username=bot_username, button_text="Just Ack", timeout_sec=5)
    )

    assert isinstance(press_responses, list)
    assert not any(r.message_text for r in press_responses if r.response_type == ResponseType.MESSAGE), \
        f"Pressing 'Just Ack' should not result in new messages, got: {press_responses}"

def test_delay_test(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # 1. Send /delay_test to get the message with the button
    send_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/delay_test", timeout_sec=5)
    )

    assert len(send_responses) == 2, f"Expected 2 messages from /delay_test, got: {send_responses}"
    assert send_responses[0].message_text == "Waiting for 3 seconds..."
    assert send_responses[1].message_text == "Done waiting!"


def test_reply_keyboard(teletest_client, ping_bot):
    bot_username = os.getenv("TELEGRAM_TEST_BOT_USERNAME")
    assert bot_username, "TELEGRAM_TEST_BOT_USERNAME environment variable not set"

    # Send command to show reply keyboard
    show_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/reply_kb", timeout_sec=5)
    )

    choose_msg = find_message_with_text(show_responses, "Choose an option:")
    assert choose_msg, f"Did not find reply keyboard message in {show_responses}"
    assert choose_msg.reply_markup, "Reply keyboard not present on message"
    assert choose_msg.reply_keyboard is True
    assert choose_msg.reply_markup[0][0].text == "Option 1"

    # Select first option using send_message
    press_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="Option 1", timeout_sec=5)
    )
    selected = find_message_with_text(press_responses, "You chose option 1")
    assert selected, f"Response to reply keyboard selection not found in {press_responses}"
    assert selected.reply_keyboard is False

    # Remove keyboard to not interfere with other tests
    remove_responses = teletest_client.send_message(
        SendMessageRequest(bot_username=bot_username, message_text="/remove_kb", timeout_sec=5)
    )
    remove_msg = find_message_with_text(remove_responses, "Keyboard removed")
    assert remove_msg, f"Remove keyboard response not found in {remove_responses}"
