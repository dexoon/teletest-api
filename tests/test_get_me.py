import os
import pytest
from teletest_api_client import User

pytestmark = pytest.mark.asyncio

async def test_get_me(teletest_client):
    user = await teletest_client.get_me()
    assert isinstance(user, User)
    assert isinstance(user.user_id, int)

    # We can check other fields if we assume we are logged in as a specific user,
    # but for general testing, checking the ID type is good enough to verify
    # the object structure and successful API call.
    if user.username:
        assert isinstance(user.username, str)
    if user.first_name:
        assert isinstance(user.first_name, str)
    if user.last_name:
        assert isinstance(user.last_name, str)
    if user.phone:
        assert isinstance(user.phone, str)
