# Use a stable Python + Node.js base image
FROM nikolaik/python-nodejs:python3.10-nodejs20

# Fix Debian repositories and install dependencies
RUN sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g' /etc/apt/sources.list && \
    sed -i '/security.debian.org/d' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg aria2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy all project files
COPY . /app/
WORKDIR /app/

# Upgrade pip and install requirements
RUN python -m pip install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir --upgrade --requirement requirements.txt

# Start your application
CMD ["bash", "start"]
