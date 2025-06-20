import os
import pytest
from pathlib import Path
import importlib
# pytest-docker uses the docker SDK, ensure it's available or handle potential import errors if necessary.
# from docker.models.containers import Container # For type hinting, if desired.


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Override default to point to real_bot's docker-compose.yml.
    
    pytestconfig is a standard pytest fixture.
    """
    return Path(__file__).parent / "real_bot" / "docker-compose.yml"

# By defining docker_compose_file and not overriding docker_setup/docker_cleanup
# to be empty, pytest-docker will automatically run `docker-compose up --build -d`
# and `docker-compose down -v` for the specified file.

@pytest.fixture(scope="session")
def real_bot_container(docker_services):
    """
    Ensures the real-bot container (defined in tests/real_bot/docker-compose.yml)
    is up and responsive.
    Yields the container object.
    """
    real_bot_service_name = "real-bot"  # Must match the service name in docker-compose.yml

    # Define a check function for wait_until_responsive
    def is_bot_responsive():
        try:
            # docker_services.get() returns a docker.models.containers.Container
            container = docker_services.get(real_bot_service_name)
            container.reload()  # Refresh container state
            # A more robust check could involve checking logs for a startup message
            # or a healthcheck endpoint if the bot had one.
            return container.status == "running"
        except Exception:
            # This can happen if the container is not found or Docker daemon is not responding
            return False

    # Wait for the service to be responsive.
    # pytest-docker would have already attempted to start services based on docker_setup.
    docker_services.wait_until_responsive(
        timeout=60.0, pause=2.0, check=is_bot_responsive
    )

    container = docker_services.get(real_bot_service_name)
    yield container
    
    # Cleanup (docker-compose down) is handled by pytest-docker automatically
    # at the end of the session due to the docker_cleanup fixture.

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
