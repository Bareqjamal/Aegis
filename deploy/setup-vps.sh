#!/bin/bash
# =============================================================================
# Project Aegis — VPS Initial Setup (Hetzner CX22, Ubuntu 24.04)
# =============================================================================
# Run as root on a fresh VPS:
#   curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/deploy/setup-vps.sh | bash
# =============================================================================

set -euo pipefail

echo "=== Project Aegis VPS Setup ==="

# ---------------------------------------------------------------------------
# 1. System updates
# ---------------------------------------------------------------------------
apt-get update && apt-get upgrade -y
apt-get install -y curl git ufw fail2ban nginx

# ---------------------------------------------------------------------------
# 2. Docker
# ---------------------------------------------------------------------------
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Docker Compose plugin (included in modern Docker)
docker compose version || apt-get install -y docker-compose-plugin

# ---------------------------------------------------------------------------
# 3. Firewall
# ---------------------------------------------------------------------------
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Cloudflare proxy)
ufw allow 443/tcp   # HTTPS (if needed)
ufw --force enable

# ---------------------------------------------------------------------------
# 4. Fail2ban (brute-force protection)
# ---------------------------------------------------------------------------
systemctl enable fail2ban
systemctl start fail2ban

# ---------------------------------------------------------------------------
# 5. Create app directory
# ---------------------------------------------------------------------------
mkdir -p /opt/aegis
cd /opt/aegis

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Clone your repo:     cd /opt/aegis && git clone YOUR_REPO ."
echo "  2. Create .env:         cp .env.example .env && nano .env"
echo "  3. Start the app:       docker compose up -d"
echo "  4. Configure Nginx:     cp deploy/nginx.conf /etc/nginx/sites-available/aegis"
echo "                          ln -s /etc/nginx/sites-available/aegis /etc/nginx/sites-enabled/"
echo "                          nginx -t && systemctl reload nginx"
echo "  5. Point DNS:           A record → $(curl -4 -s ifconfig.me)"
echo ""
