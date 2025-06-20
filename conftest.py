import os
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def real_bot_ready(docker_services):
    """Wait until the real-bot container is ready."""
    def is_responsive():
        # You can implement a better health check if your bot exposes an HTTP endpoint
        # For now, just return True after a delay
        return True

    docker_services.wait_until_responsive(
        timeout=60.0, pause=2.0, check=is_responsive
    )
    yield

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Setup environment variables for tests."""
    # Ensure we have the required environment variables for real bot tests
    required_vars = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH", 
        "TELEGRAM_SESSION_STRING",
        "TELEGRAM_BOT_TOKEN",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(f"Missing required environment variables for real bot tests: {missing_vars}")

    import src.app as app_module
    import importlib
    importlib.reload(app_module)
    yield app_module 