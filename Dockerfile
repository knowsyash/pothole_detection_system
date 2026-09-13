# okDRIVER AI Backend - Production Dockerfile for Hugging Face Spaces & Cloud
FROM python:3.11-slim

# Prevent Python from writing .pyc files & enable unbuffered standard I/O
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies required for OpenCV, PyTorch, and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Standard for Hugging Face Spaces security)
RUN useradd -m -u 1000 user && \
    mkdir -p /app && \
    chown -R user:user /app /home/user

WORKDIR /app

# Copy dependency specifications first for optimal Docker layer caching
COPY --chown=user:user requirements.txt ./root-requirements.txt
COPY --chown=user:user backend/requirements.txt ./backend-requirements.txt

# Install Python dependencies as root, then switch to user
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./root-requirements.txt && \
    pip install --no-cache-dir -r ./backend-requirements.txt

# Copy okdriver core computer vision package and install in editable mode
COPY --chown=user:user okdriver/ ./okdriver/
COPY --chown=user:user pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

# Copy backend source code
COPY --chown=user:user backend/ ./backend/

# Switch to non-root user
USER user

# Pre-cache YOLOv8 pothole model weights into user cache directory during build
RUN python -c "from okdriver import PotholeDetector; PotholeDetector()"

WORKDIR /app/backend

# Expose standard Hugging Face Spaces port (7860) and standard FastAPI port (8000)
EXPOSE 7860
EXPOSE 8000

# Start FastAPI production server listening on port 7860 (Hugging Face default)
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
