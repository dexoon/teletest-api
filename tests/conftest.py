import os
import pytest
import importlib
import logging
import subprocess
import shutil
import uuid
import pathlib
from dotenv import load_dotenv

# Configure logging for conftest
# To see these logs with pytest, you might need:
# pytest -o log_cli=true -o log_cli_level=INFO -s (the -s flag captures stdout/stderr and loggin)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@pytest.fixture(scope="session")
def real_bot_container(request):
    """
    Fixture to build and run the real_bot Docker container for testing.
    Loads environment variables from .env.test for the container and test session.
    """
    logger.info("Setting up real_bot_container fixture (session-scoped).")
    project_root = pathlib.Path(__file__).resolve().parent.parent
    env_file_path = project_root / ".env.test"
    logger.info(f"Attempting to load environment variables from: {env_file_path}")

    if not env_file_path.is_file():
        msg = f".env.test file not found at {env_file_path}. Please create it with necessary environment variables."
        logger.error(msg)
        pytest.exit(msg, returncode=1) # Exit pytest if .env.test is crucial and missing

    # Load .env.test into the current environment.
    # override=True ensures .env.test values take precedence over existing env vars.
    loaded_successfully = load_dotenv(dotenv_path=env_file_path, override=True)
    if loaded_successfully:
        logger.info(f"Successfully loaded environment variables from {env_file_path}.")
        # Log some key variables to confirm they are loaded (show only if SET or NOT SET for security)
        for var_name in ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION_STRING", "TELEGRAM_BOT_TOKEN", "TELEGRAM_TEST_BOT_USERNAME"]:
            logger.info(f"  Var {var_name} after load_dotenv: {'SET' if os.getenv(var_name) else 'NOT SET'}")
    else:
        logger.warning(f"dotenv.load_dotenv() reported no variables loaded from {env_file_path} (file might be empty or only comments).")


    if not shutil.which("docker"):
        msg = "Docker command not found. Please install Docker and ensure it's in your PATH."
        logger.error(msg)
        pytest.exit(msg, returncode=1) # Exit if docker is essential

    docker_image_name = "real_test_bot_image"
    docker_container_name = f"real-test-bot-container-{uuid.uuid4().hex[:8]}"
    docker_context_dir = str(project_root / "tests" / "real_bot")
    logger.info(f"Docker image name: {docker_image_name}, Container name: {docker_container_name}, Context: {docker_context_dir}")

    try:
        logger.info(f"Building Docker image '{docker_image_name}' from context '{docker_context_dir}'...")
        subprocess.check_call(
            ["docker", "build", "-t", docker_image_name, docker_context_dir],
            cwd=str(project_root),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logger.info(f"Docker image '{docker_image_name}' built successfully.")

        logger.info(f"Running Docker container '{docker_container_name}' from image '{docker_image_name}' with env from '{env_file_path}'...")
        subprocess.check_call([
            "docker", "run",
            "-d",
            "--name", docker_container_name,
            "--env-file", str(env_file_path),
            docker_image_name
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Docker container '{docker_container_name}' started.")

    except subprocess.CalledProcessError as e:
        stdout = e.stdout.decode('utf-8', errors='replace') if e.stdout else "N/A"
        stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else "N/A"
        error_msg = f"Failed to build or run Docker container: {e}\nStdout:\n{stdout}\nStderr:\n{stderr}"
        logger.error(error_msg)
        pytest.fail(error_msg, pytrace=False)
    except FileNotFoundError: # pragma: no cover
        # This case should be caught by shutil.which("docker") check earlier,
        # but kept as a safeguard.
        msg = "Docker command not found during setup."
        logger.error(msg)
        pytest.fail(msg, pytrace=False)

    def cleanup_container():
        logger.info(f"Cleaning up Docker container '{docker_container_name}'...")
        # Stop the container
        stop_result = subprocess.run(["docker", "stop", docker_container_name], capture_output=True, text=True)
        if stop_result.returncode == 0:
            logger.info(f"Container '{docker_container_name}' stopped successfully.")
        else:
            logger.warning(f"Could not stop container '{docker_container_name}'. It might already be stopped or an error occurred. stderr: {stop_result.stderr.strip()}")

        # Remove the container
        remove_result = subprocess.run(["docker", "rm", docker_container_name], capture_output=True, text=True)
        if remove_result.returncode == 0:
            logger.info(f"Container '{docker_container_name}' removed successfully.")
        else:
            logger.warning(f"Could not remove container '{docker_container_name}'. It might already be removed or an error occurred. stderr: {remove_result.stderr.strip()}")

    request.addfinalizer(cleanup_container)

    # Optional: Add a small delay or a health check here to ensure the bot inside the container has started.
    # import time
    # logger.info("Waiting a few seconds for the bot in container to initialize...")
    # time.sleep(5) # Give a moment for the container to be fully up if needed

    # Execute get_me.py inside the container to fetch the bot's username
    try:
        logger.info(f"Executing get_me.py in container '{docker_container_name}' to fetch bot username...")
        # Ensure get_me.py is executable if needed, though python execution should be fine.
        # The script get_me.py is expected to be in /app within the container.
        completed_process = subprocess.run(
            ["docker", "exec", docker_container_name, "python", "get_me.py"],
            capture_output=True, text=True, check=True, timeout=30 # Added timeout
        )
        bot_username_from_docker = completed_process.stdout.strip()
        if not bot_username_from_docker or "Error:" in bot_username_from_docker:
            error_msg = f"Failed to get bot username from get_me.py. Output: {bot_username_from_docker}"
            logger.error(error_msg)
            pytest.fail(error_msg, pytrace=False)
        
        os.environ['TELEGRAM_TEST_BOT_USERNAME'] = bot_username_from_docker
        logger.info(f"Successfully fetched and set TELEGRAM_TEST_BOT_USERNAME='{bot_username_from_docker}'")

    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip() if e.stdout else "N/A"
        stderr = e.stderr.strip() if e.stderr else "N/A"
        error_msg = f"Failed to execute get_me.py in container: {e}\nStdout:\n{stdout}\nStderr:\n{stderr}"
        logger.error(error_msg)
        pytest.fail(error_msg, pytrace=False)
    except subprocess.TimeoutExpired:
        error_msg = f"Timeout while executing get_me.py in container '{docker_container_name}'."
        logger.error(error_msg)
        pytest.fail(error_msg, pytrace=False)


    logger.info(f"real_bot_container setup complete, yielding container name: {docker_container_name}")
    yield docker_container_name


@pytest.fixture # function scope by default
def app():
    """
    Fixture to provide the FastAPI app instance.
    Ensures required environment variables are set (loaded by real_bot_container)
    and reloads the app module to pick up any environment changes.
    """
    logger.info("Setting up app fixture (function-scoped).")
    required_vars = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_SESSION_STRING",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_TEST_BOT_USERNAME",
    ]
    logger.info(f"Checking for required environment variables: {required_vars}")
    for var_name in required_vars:
        var_value = os.getenv(var_name)
        # Log only presence for security, actual values should not be logged unless for specific non-sensitive debug vars.
        logger.info(f"  Env var {var_name}: {'SET' if var_value else 'NOT SET'}")

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        skip_message = f"Missing required environment variables: {', '.join(missing_vars)}. These should be in .env.test and loaded by real_bot_container. Skipping test."
        logger.warning(skip_message)
        pytest.skip(skip_message)

    logger.info("All required environment variables are set.")
    logger.info("Reloading src.app module to pick up environment variables...")
    import src.app as app_module
    importlib.reload(app_module)
    logger.info("src.app module reloaded.")

    return app_module.app
