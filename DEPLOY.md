# Project Aegis — Deployment Guide

## Quick Start (Your Laptop)

Double-click `run.bat` or run:

```bash
run.bat
```

This installs dependencies, starts the **Brain Server** (background), and opens the **Dashboard**. Both run together.

### Individual commands:

| Command | What it does |
|---------|-------------|
| `run.bat` | Full start: dashboard + brain server |
| `run.bat dashboard` | Dashboard only (port 8501) |
| `run.bat server` | Brain server only (port 8502) |
| `run.bat status` | Check if services are running |
| `run.bat stop` | Stop the brain server |
| `run.bat brain` | Run one scan cycle manually |
| `run.bat help` | Show all commands |

### Ports:
- **8501** — Streamlit Dashboard (your trading terminal)
- **8502** — Brain API (health checks, status, manual triggers)

### The problem with laptops:
When you close the laptop, everything stops. For 24/7 operation, deploy to a server (see below).

---

## Server Deployment (24/7 — Recommended)

### Option 1: Docker Compose (Easiest)

**Requirements:** A Linux VPS with Docker installed ($4-6/month: Hetzner CX22, DigitalOcean Basic, etc.)

```bash
# 1. Clone the repo on your server
git clone https://github.com/YOUR_REPO/project-aegis.git
cd project-aegis

# 2. Create your .env file
cp .env.example .env
nano .env   # edit your settings

# 3. Start everything
docker compose up -d

# 4. Check it's running
docker compose ps
docker compose logs -f aegis-brain
```

**What runs:**
- `aegis` — Streamlit dashboard on port 8501
- `aegis-brain` — Background brain (scan every 30 min, morning email at 7 AM UTC)

**Both share the same data** via Docker volumes — the brain writes scan results, the dashboard reads them.

```bash
# Useful commands
docker compose logs -f aegis-brain    # Watch brain logs
docker compose restart aegis-brain    # Restart brain only
docker compose down                   # Stop everything
docker compose up -d --build          # Rebuild after code changes

# Check brain status
curl http://localhost:8502/health
curl http://localhost:8502/api/brain/status
curl http://localhost:8502/api/brain/report
```

### Option 2: systemd (Linux without Docker)

```bash
# 1. Install Python 3.11+ and dependencies
sudo apt update && sudo apt install python3.11 python3.11-venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create systemd service for the brain
sudo nano /etc/systemd/system/aegis-brain.service
```

Paste this:
```ini
[Unit]
Description=Aegis Brain — Background Market Scanner
After=network.target

[Service]
Type=simple
User=aegis
WorkingDirectory=/opt/project-aegis
Environment=PYTHONPATH=/opt/project-aegis
ExecStart=/opt/project-aegis/venv/bin/python src/brain_entrypoint.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 3. Create systemd service for the dashboard
sudo nano /etc/systemd/system/aegis-dashboard.service
```

Paste this:
```ini
[Unit]
Description=Aegis Dashboard — Streamlit
After=network.target aegis-brain.service

[Service]
Type=simple
User=aegis
WorkingDirectory=/opt/project-aegis
Environment=PYTHONPATH=/opt/project-aegis
ExecStart=/opt/project-aegis/venv/bin/python -m streamlit run dashboard/app.py --server.headless true --server.port 8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 4. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable aegis-brain aegis-dashboard
sudo systemctl start aegis-brain aegis-dashboard

# 5. Check status
sudo systemctl status aegis-brain
sudo systemctl status aegis-dashboard
journalctl -u aegis-brain -f    # live logs
```

---

## Environment Variables

Set these in `.env` (Docker) or as system env vars (systemd):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8501` | Dashboard port |
| `BRAIN_PORT` | `8502` | Brain API port |
| `BRAIN_INTERVAL_MIN` | `30` | Minutes between brain cycles |
| `MORNING_EMAIL_HOUR` | `7` | Hour (UTC) to send morning emails |
| `MORNING_EMAIL_MIN` | `0` | Minute to send morning emails |
| `AEGIS_SMTP_HOST` | — | SMTP server (e.g., smtp.gmail.com) |
| `AEGIS_SMTP_PORT` | `587` | SMTP port |
| `AEGIS_SMTP_USER` | — | SMTP username |
| `AEGIS_SMTP_PASS` | — | SMTP password or app password |
| `AEGIS_SMTP_FROM` | — | Sender email address |

### Gmail setup for morning emails:
1. Enable 2-factor auth on your Google account
2. Go to Google Account > Security > App passwords
3. Create an app password for "Mail"
4. Use your Gmail as `AEGIS_SMTP_USER` and the app password as `AEGIS_SMTP_PASS`

---

## Brain API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (for Docker/monitoring) |
| `GET` | `/api/brain/status` | Current status, cycle count, last error |
| `GET` | `/api/brain/report` | Last full cycle report |
| `GET` | `/api/brain/config` | Current configuration |
| `POST` | `/api/brain/trigger` | Manually trigger a brain cycle |
| `POST` | `/api/email/trigger` | Manually trigger morning email |

Trigger endpoints are rate-limited to 1 per 5 minutes.

---

## Architecture

```
Your Laptop / Server
├── aegis (Streamlit) ────── Port 8501
│   └── Reads: brain_status.json, watchlist_summary.json, etc.
│
├── aegis-brain (FastAPI) ── Port 8502
│   ├── APScheduler
│   │   ├── Brain Cycle ─── Every 30 min
│   │   │   ├── Market scan (12 assets)
│   │   │   ├── Social sentiment
│   │   │   ├── Auto-trade decisions
│   │   │   ├── Alert checks
│   │   │   ├── Prediction validation
│   │   │   ├── Market discovery
│   │   │   └── Daily reflection
│   │   └── Morning Email ── Daily at 7:00 UTC
│   └── FastAPI (health + status + triggers)
│
└── Shared Data (JSON files)
    ├── src/data/ ────── Scan results, brain status, charts
    ├── memory/ ──────── Predictions, portfolio, lessons
    └── users/ ───────── User profiles, sessions
```

Both services read/write the same JSON files. No database required.

---

## Recommended Server Specs

| Users | Server | Cost |
|-------|--------|------|
| 1-10 | Hetzner CX22 (2 vCPU, 4GB RAM) | ~$4/mo |
| 10-50 | Hetzner CX32 (4 vCPU, 8GB RAM) | ~$8/mo |
| 50+ | Consider PostgreSQL migration | ~$15/mo |

The brain cycle uses ~500MB RAM during market scans. The dashboard uses ~200MB. Total: under 1GB for a single-user setup.
