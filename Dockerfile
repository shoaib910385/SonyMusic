# Use official Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables for non-interactive installs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies, Node.js 19, ffmpeg, aria2
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg ffmpeg aria2 build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_19.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only requirements first for caching
COPY requirements.txt /app/

# Upgrade pip and install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . /app/

# Expose default port for Heroku (optional if web dyno)
ENV PORT=8080

# Start the bot
CMD ["bash", "start"]
