import os
import pytest
from pathlib import Path
import importlib


@pytest.fixture(scope="session")
def docker_setup():
    """Override default docker_setup to prevent docker-compose up."""
    return []

@pytest.fixture(scope="session")
def docker_cleanup():
    """Override default docker_cleanup to prevent docker-compose down."""
    return []


@pytest.fixture(scope="session")
def real_bot_container(docker_services):
    """Build and run the real-bot container directly."""
    # Build the image
    docker_services.build_image(
        "real-bot",
        path=str(Path(__file__).parent.parent / "tests" / "real_bot"),
        dockerfile="Dockerfile"
    )
    
    # Run the container
    container = docker_services.run_container(
        "real-bot",
        image="real-bot",
        environment={
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN")
        }
    )
    
    # Wait for container to be ready
    def is_responsive():
        try:
            # Check if the container is running and the process is active
            container.reload()
            return container.status == "running"
        except:
            return False

    docker_services.wait_until_responsive(
        timeout=60.0, pause=2.0, check=is_responsive
    )
    
    yield container
    
    # Cleanup is handled automatically by pytest-docker

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
