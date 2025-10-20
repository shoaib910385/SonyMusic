# Use official Python 3.9 slim image
FROM python:3.9-slim

# Install curl, gnupg (for Node setup), ffmpeg, and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg ffmpeg aria2 && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory and copy project files
WORKDIR /app
COPY . /app/

# Upgrade pip and install dependencies
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Start the app
CMD ["bash", "start"]
