# Use Python 3.10 slim image from GitHub Container Registry (bypasses Docker Hub)
FROM ghcr.io/cs01/python-node:3.10-19

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg aria2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt /app/

# Upgrade pip and install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . /app/

# Expose port (optional, useful for web dyno)
ENV PORT=8080

# Start your bot
CMD ["bash", "start"]
