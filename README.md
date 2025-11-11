# 🧰 Frigate Backup Manager

A lightweight, self-contained management tool for **Frigate NVR** systems running in Docker on Debian.  
It provides automatic configuration backups, Google Drive sync, OS and Frigate updates, and driver management — all from a simple web UI.

---

## 🚀 Features

- 📦 **Automated Backups** — Local rotation and optional Google Drive upload  
- 🔁 **One-Click Restore** — Restore from local or cloud backups  
- 🧠 **Driver Detection & Install** — Coral TPU, Intel, NVIDIA, AMD  
- ⚙️ **System Maintenance** — Update OS, Frigate, and apply security patches  
- ☁️ **Google Drive Integration** — User-supplied token, no secrets needed  
- 🧩 **Home Assistant Friendly** — Exposes status API and MQTT-ready  
- 🌙 **Cron Scheduling** — Fully configurable via UI  
- 💡 **Minimal Setup** — Just Docker or Docker Compose

---

## 🐳 Quick Start (GitHub Container Registry)

Once the repository is published, you can deploy directly from GitHub:

```bash
docker pull ghcr.io/<yourusername>/frigate-backup-manager:latest
mkdir -p data logs backups
docker run -d   -p 8082:8082   -v $(pwd)/data:/data   -v $(pwd)/logs:/logs   -v $(pwd)/backups:/backups   -v /etc/frigate:/config:ro   -v $(pwd)/drive_token.json:/data/drive_token.json:ro   -v /var/run/docker.sock:/var/run/docker.sock   --name frigate-backup-manager   ghcr.io/<yourusername>/frigate-backup-manager:latest
```

Or using **Docker Compose**:

```bash
git clone https://github.com/<yourusername>/frigate-backup-manager.git
cd frigate-backup-manager
docker compose pull
docker compose up -d
```

Then visit **http://<your-host>:8082** for the dashboard.

---

## 🧾 Environment Variables

| Variable | Default | Description |
|-----------|----------|-------------|
| `TZ` | `Europe/London` | Timezone |
| `DATA_DIR` | `/data` | Persistent configuration |
| `LOG_DIR` | `/logs` | Log directory |
| `BACKUP_DIR` | `/backups` | Where backups are stored |
| `CONFIG_FILE` | `/data/config.json` | App configuration file |
| `GDRIVE_TOKEN` | `/data/drive_token.json` | Google Drive credentials file |

---

## 🔐 Google Drive Setup

1. Create a Google OAuth “Desktop App” at [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).  
2. Download `credentials.json`.  
3. On your PC, run:
   ```bash
   pip install google-auth-oauthlib google-auth google-api-python-client
   python -m google_auth_oauthlib.flow --client-secrets credentials.json --scopes https://www.googleapis.com/auth/drive.file
   ```
4. It will open a browser — sign in and save `token.json`.
5. Rename it to `drive_token.json` and place it in the repository root.

---

## 🖥️ Web Interface

### Default URL
```
http://<IP ADDRESS>:8082
```

**Main sections:**
- 🧩 Backups & Restore  
- ☁️ Google Drive Sync  
- ⚙️ Hardware & Drivers  
- 🧱 System Actions  
- 📜 Real-time Logs

---

## ⚙️ Docker Commands

**Rebuild locally:**
```bash
docker compose build
docker compose up -d
```

**Pull latest image from GHCR:**
```bash
docker compose pull
docker compose up -d
```

**View logs:**
```bash
docker compose logs -f frigate-backup-manager
```

**Stop and remove:**
```bash
docker compose down
```

---

## 📜 License
MIT License © 2025 ShephC260