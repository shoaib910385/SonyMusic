# Use official Python 3.10 image
FROM python:3.10-slim

# Install Node.js 19, ffmpeg, and aria2
RUN apt-get update && apt-get install -y curl gnupg ffmpeg aria2 && \
    curl -fsSL https://deb.nodesource.com/setup_19.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/
WORKDIR /app/

# Upgrade pip and install requirements
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Start your app
CMD ["bash", "start"]
