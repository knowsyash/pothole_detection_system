# okDRIVER Backend Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user && \
    mkdir -p /app && \
    chown -R user:user /app /home/user

WORKDIR /app

COPY --chown=user:user requirements.txt ./root-requirements.txt
COPY --chown=user:user backend/requirements.txt ./backend-requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./root-requirements.txt && \
    pip install --no-cache-dir -r ./backend-requirements.txt

COPY --chown=user:user okdriver/ ./okdriver/
COPY --chown=user:user pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

COPY --chown=user:user backend/ ./backend/

USER user

RUN python -c "from okdriver import PotholeDetector; PotholeDetector()"

WORKDIR /app/backend

EXPOSE 7860
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
