import os
import pytest
import importlib
# pytest-docker is no longer used, so no need to import docker SDK types.


@pytest.fixture
def app():
    """
    Fixture to provide the FastAPI app instance.
    Ensures required environment variables are set and reloads the app module
    to pick up any environment changes.
    """
    # Ensure we have the required environment variables for the main app and real bot tests
    required_vars = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_SESSION_STRING",
        "TELEGRAM_BOT_TOKEN",  # Though used by the bot in container, good to check if tests rely on its presence
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    import src.app as app_module

    # Reload the app module to ensure it picks up environment variables
    # This is important because src.app loads env vars at module level.
    importlib.reload(app_module)

    return app_module.app  # Return the FastAPI instance
