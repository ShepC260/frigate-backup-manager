FROM debian:bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Base packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    tzdata curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create runtime dirs
RUN mkdir -p /data /logs /backups /app/static /app/templates

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r /app/requirements.txt

# App code
COPY app /app

EXPOSE 8082

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
