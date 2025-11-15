FROM debian:bookworm-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    curl git cron \
    build-essential dkms apt-transport-https ca-certificates gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create Python venv to bypass "externally-managed" issues
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create dirs
RUN mkdir -p /data /logs /backups /config /app/static

# Copy app
COPY app /app

# Install Python requirements into venv
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8082

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
