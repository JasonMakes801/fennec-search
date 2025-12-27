FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (FFmpeg for video, build tools for insightface)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (but in dev, we mount over this)
COPY . .

CMD ["python", "main.py"]
