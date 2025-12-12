import importlib
import logging
import os
import subprocess
import sys
import threading
import time
from typing import AsyncGenerator

import aiohttp
import pytest
import pytest_asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Add clients/python-client to path to import TeletestApiClient
sys.path.append(os.path.join(os.path.dirname(__file__), "../clients/python-client"))
from teletest_api_client import TeletestApiClient

# Configure logging for conftest
# To see these logs with pytest, you might need:
# pytest -o log_cli=true -o log_cli_level=INFO -s (the -s flag captures stdout/stderr and loggin)
debug_mode = os.getenv("DEBUG", "0").lower() in ("1", "true", "yes")
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG if debug_mode else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@pytest.fixture(scope="session", autouse=True)
def ping_bot(request):
    # Start the bot
    proc = subprocess.Popen(
        [sys.executable, "tests/real_bot/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Execute get_me.py inside the container to fetch the bot's username
    try:
        logger.info("Executing get_me.py to fetch bot username...")
        # Ensure get_me.py is executable if needed, though python execution should be fine.
        # The script get_me.py is expected to be in /app within the container.
        completed_process = subprocess.run(
            [sys.executable, "tests/real_bot/get_me.py"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,  # Added timeout
        )
        bot_username_from_get_me = completed_process.stdout.strip()
        if not bot_username_from_get_me or "Error:" in bot_username_from_get_me:
            error_msg = f"Failed to get bot username from get_me.py. Output: {bot_username_from_get_me}"
            logger.error(error_msg)
            pytest.fail(error_msg, pytrace=False)

        os.environ["TELEGRAM_TEST_BOT_USERNAME"] = bot_username_from_get_me
        logger.info(
            f"Successfully fetched and set TELEGRAM_TEST_BOT_USERNAME='{bot_username_from_get_me}'"
        )

    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip() if e.stdout else "N/A"
        stderr = e.stderr.strip() if e.stderr else "N/A"
        error_msg = (
            f"Failed to execute get_me.py: {e}\nStdout:\n{stdout}\nStderr:\n{stderr}"
        )
        logger.error(error_msg)
        pytest.fail(error_msg, pytrace=False)
    except subprocess.TimeoutExpired:
        error_msg = "Timeout while executing get_me.py."
        logger.error(error_msg)
        pytest.fail(error_msg, pytrace=False)
    time.sleep(3)  # Wait for bot to start up, or better: poll for readiness

    yield  # Run tests

    # Teardown
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture(scope="session")
def app_instance():
    """
    Fixture to provide the FastAPI app instance.
    Ensures required environment variables are set (loaded by ping_bot)
    and reloads the app module to pick up any environment changes.
    """
    logger.info("Setting up app fixture (session-scoped).")
    required_vars = [
        "API_ID",
        "API_HASH",
        "SESSION_STRING",
        "TEST_BOT_TOKEN",
        "TELEGRAM_TEST_BOT_USERNAME",
    ]
    logger.info(f"Checking for required environment variables: {required_vars}")
    for var_name in required_vars:
        var_value = os.getenv(var_name)
        # Log only presence for security, actual values should not be logged unless for specific non-sensitive debug vars.
        logger.info(f"  Env var {var_name}: {'SET' if var_value else 'NOT SET'}")

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        skip_message = f"Missing required environment variables: {', '.join(missing_vars)}. These should be in .env.test and loaded by ping_bot. Skipping test."
        logger.warning(skip_message)
        pytest.skip(skip_message)

    logger.info("All required environment variables are set.")
    logger.info("Reloading src.app module to pick up environment variables...")
    import src.app as app_module

    importlib.reload(app_module)
    logger.info("src.app module reloaded.")

    return app_module.app


@pytest.fixture(scope="session")
def server(app_instance):
    """
    Starts uvicorn server in a separate thread.
    Returns the base URL.
    """
    # Pick a random port or fixed port.
    port = 8001
    host = "127.0.0.1"
    base_url = f"http://{host}:{port}"

    config = uvicorn.Config(app_instance, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run)
    thread.start()

    # Wait for server to start
    # We can ping it or just simple sleep, or use uvicorn's startup flag if we had access to it easily.
    # Simple sleep for now, but better would be retry-connect.
    time.sleep(2)

    yield base_url

    server.should_exit = True
    thread.join()


@pytest_asyncio.fixture
async def teletest_client(server) -> AsyncGenerator[TeletestApiClient, None]:
    """
    Fixture to provide the TeletestApiClient instance.
    """
    async with aiohttp.ClientSession() as session:
        yield TeletestApiClient(base_url=server, session=session)
