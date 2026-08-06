#!/bin/bash
exec </dev/tty 2>/dev/null

REPO_URL="https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main"

echo "🚀 Setting up vps-deploy directory..."
mkdir -p vps-deploy

if [ -f "test.env" ]; then
    cp test.env vps-deploy/.env
    echo "✅ Copied local test.env to vps-deploy/.env"
else
    curl -sL "$REPO_URL/test.env" -o vps-deploy/.env 2>/dev/null || true
    echo "✅ Checked/Downloaded .env configuration!"
fi

if [ -f "requirements.txt" ]; then
    cp requirements.txt vps-deploy/
else
    curl -sL "$REPO_URL/requirements.txt" -o vps-deploy/requirements.txt
fi

if [ -f "bot.py" ]; then
    cp bot.py vps-deploy/
else
    curl -sL "$REPO_URL/bot.py" -o vps-deploy/bot.py
fi

cd vps-deploy || exit

echo "📦 Installing system dependencies (Python & Docker)..."
if command -v apt &> /dev/null; then
    sudo apt update
    sudo apt install -y python3-pip python3-venv curl docker.io docker-compose
elif command -v yum &> /dev/null; then
    sudo yum install -y python3-pip curl docker docker-compose
fi

echo "⚙️ Starting and enabling Docker service..."
if command -v systemctl &> /dev/null && systemctl list-units &> /dev/null; then
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER 2>/dev/null || true
else
    echo "⚠️ systemctl not fully available. Attempting to start docker daemon..."
    nohup sudo dockerd > /dev/null 2>&1 &
fi

echo "🔧 Configuring Python pip..."
mkdir -p ~/.config/pip 
echo -e "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Ensure python docker and psutil libraries are present
pip install docker psutil --break-system-packages 2>/dev/null || true

echo "🛠️ Checking systemd service setup for bot..."
SERVICE_FILE="/etc/systemd/system/bot.service"
CURRENT_DIR=$(pwd)

if command -v systemctl &> /dev/null && systemctl list-units &> /dev/null; then
    sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Vps Discord Bot
After=network.target docker.service
Requires=docker.service

[Service]
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/python3 $CURRENT_DIR/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable bot
    sudo systemctl restart bot
    echo "✨ Installation, Docker setup, and systemd service configuration completed successfully!"
else
    echo "⚠️ systemd/systemctl not available in this container environment."
    echo "✨ Installation complete! You can run and manage your bot using the 24/7 manager."
fi
