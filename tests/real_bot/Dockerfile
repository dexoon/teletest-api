FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the real_bot code
COPY real_bot.py ./
COPY get_me.py ./

# Set environment variables
ENV PYTHONPATH=/app

# Run the real bot
CMD ["python", "real_bot.py"] 
