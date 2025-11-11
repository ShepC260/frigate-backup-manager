# ==========================================
# Frigate Backup Manager - Dockerfile
# ==========================================

FROM debian:bookworm-slim

# ---- System setup ----
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv curl git cron \
    build-essential dkms apt-transport-https ca-certificates \
    gnupg lsb-release wget unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Create app directories ----
WORKDIR /app
RUN mkdir -p /data /logs /backups /config

# ---- Copy application source ----
COPY app /app

# ---- Install Python dependencies ----
RUN pip install --no-cache-dir \
    fastapi uvicorn jinja2 apscheduler cron-descriptor \
    google-auth google-auth-oauthlib google-api-python-client \
    google-auth-httplib2 requests

# ---- Environment defaults ----
ENV LOG_DIR=/logs \
    BACKUP_DIR=/backups \
    CONFIG_DIR=/config \
    CONFIG_FILE=/data/config.json \
    PYTHONUNBUFFERED=1

# ---- Expose the web UI port ----
EXPOSE 8082

# ---- Entrypoint ----
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
