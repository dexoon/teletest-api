FROM python:3.12-slim

WORKDIR /app

# Copy project definition and source code
COPY pyproject.toml ./
COPY teletest_api ./teletest_api

# Install the project and its dependencies
RUN pip install --no-cache-dir .

# CMD runs the installed module
CMD ["python", "-m", "teletest_api"]
