FROM debian:bookworm-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    curl git cron \
    build-essential dkms apt-transport-https ca-certificates gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create Python venv to bypass PEP 668 "externally managed" errors
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create required directories
RUN mkdir -p /data /logs /backups /config /app/static

# Copy requirements file first (better cache) and install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY app /app

EXPOSE 8082

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
