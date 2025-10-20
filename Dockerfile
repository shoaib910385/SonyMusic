# Use a Bullseye-based Python + Node image
FROM nikolaik/python-nodejs:python3.10-nodejs19-bullseye

# Install ffmpeg and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy your app code
COPY . /app/
WORKDIR /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -U -r requirements.txt

# Start your bot
CMD ["bash", "start"]
