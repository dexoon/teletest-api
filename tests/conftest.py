import os
import pytest
from pathlib import Path

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
    """Simple fixture to import and return the app."""
    import src.app
    return src.app 