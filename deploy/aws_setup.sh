#!/bin/bash
# =============================================================================
# InboxIQ — AWS Production Server Initialization Script
# Target OS: Ubuntu 22.04 / 24.04 LTS on AWS Lightsail or EC2
# =============================================================================
set -e

echo "=========================================================="
echo "  Starting InboxIQ Production Setup on AWS"
echo "=========================================================="

# 1. Update and install prerequisites
echo "[1/6] Updating packages and installing dependencies..."
export DEBIAN_FRONTEND=noninteractive
sudo apt update && sudo apt upgrade -y
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release git ufw fail2ban certbot python3-certbot-nginx

# 2. Configure 4GB Swap Space (Essential safety net for multi-user OCR/pgvector)
echo "[2/6] Configuring 4GB Swap space..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    # Optimize swappiness (only use swap under extreme memory pressure)
    sudo sysctl vm.swappiness=10
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
    echo "Swap configured successfully."
else
    echo "Swapfile already exists. Skipping."
fi

# 3. Install Docker and Docker Compose Plugin
echo "[3/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
    echo "Docker installed successfully."
else
    echo "Docker is already installed."
fi

# 4. Configure Firewall (UFW)
echo "[4/6] Hardening Firewall (UFW)..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (Certbot & Web)
sudo ufw allow 443/tcp  # HTTPS (Encrypted Web)
sudo ufw --force enable
echo "Firewall enabled: Ports 22, 80, 443 open. Database & Redis strictly isolated inside Docker."

# 5. Create application directory structure
echo "[5/6] Creating application directories in /opt/inboxiq..."
sudo mkdir -p /opt/inboxiq/uploads
sudo mkdir -p /opt/inboxiq/backups
sudo mkdir -p /opt/inboxiq/logs
sudo chown -R $USER:$USER /opt/inboxiq

# 6. Configure daily automated backup & housekeeping cron
echo "[6/6] Registering nightly housekeeping cron (2:00 AM)..."
CRON_JOB="0 2 * * * cd /opt/inboxiq/backend && /usr/bin/python3 scripts/run_housekeeping.py >> /opt/inboxiq/logs/housekeeping.log 2>&1"
(crontab -l 2>/dev/null | grep -v "run_housekeeping.py" ; echo "$CRON_JOB") | crontab -

echo "=========================================================="
echo "  InboxIQ Server Initialization Completed Successfully!   "
echo "=========================================================="
echo ""
echo "Next Steps:"
echo "1. Copy your application files to /opt/inboxiq"
echo "2. Populate /opt/inboxiq/.env with production credentials"
echo "3. Run: cd /opt/inboxiq && docker compose -f docker-compose.prod.yml up -d --build"
echo "4. Issue SSL certificate: sudo certbot certonly --webroot -w /opt/inboxiq/frontend/dist -d yourdomain.com"
echo "=========================================================="
