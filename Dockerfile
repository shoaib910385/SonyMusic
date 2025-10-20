# Start from Debian slim base
FROM debian:bookworm-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/python/bin:$PATH"

# Install dependencies, Python 3.10, Node.js 19, ffmpeg, aria2
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget curl gnupg build-essential ffmpeg aria2 libffi-dev libssl-dev zlib1g-dev \
        xz-utils bzip2 ca-certificates && \
    # Install Node.js 19
    curl -fsSL https://deb.nodesource.com/setup_19.x | bash - && \
    apt-get install -y nodejs && \
    # Install Python 3.10 from source (minimal)
    wget https://www.python.org/ftp/python/3.10.16/Python-3.10.16.tgz && \
    tar -xvf Python-3.10.16.tgz && \
    cd Python-3.10.16 && \
    ./configure --enable-optimizations --prefix=/opt/python && \
    make -j$(nproc) && make install && \
    cd .. && rm -rf Python-3.10.16 Python-3.10.16.tgz && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
COPY requirements.txt /app/

# Upgrade pip and install dependencies
RUN /opt/python/bin/python3.10 -m pip install --no-cache-dir --upgrade pip && \
    /opt/python/bin/python3.10 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . /app/

# Start bot
CMD ["/opt/python/bin/python3.10", "start"]
