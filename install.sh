#!/bin/bash

echo "🚀 Setting up vps-deploy directory..."
mkdir -p vps-deploy

if [ -f "test.env" ]; then
    cp test.env vps-deploy/.env
    echo "✅ Copied local test.env to vps-deploy/.env"
else
    echo "⚠️ Local test.env not found. Downloading from GitHub..."
    curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/test.env -o vps-deploy/.env
    echo "✅ Downloaded .env successfully!"
fi

if [ -f "requirements.txt" ]; then
    cp requirements.txt vps-deploy/
    echo "✅ Copied local requirements.txt to vps-deploy/"
else
    echo "⚠️ Local requirements.txt not found. Downloading from GitHub..."
    curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/requirements.txt -o vps-deploy/requirements.txt
    echo "✅ Downloaded requirements.txt successfully!"
fi

if [ -f "bot.py" ]; then
    cp bot.py vps-deploy/
    echo "✅ Copied local bot.py to vps-deploy/"
else
    echo "⚠️ Local bot.py not found. Downloading from GitHub..."
    curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/bot.py -o vps-deploy/bot.py
    echo "✅ Downloaded bot.py successfully!"
fi

cd vps-deploy || exit

echo "📦 Installing python3-pip..."
sudo apt update && sudo apt install python3-pip -y

echo "⚙️ Configuring pip..."
mkdir -p ~/.config/pip 
echo -e "[global]\nbreak-system-packages = true" > ~/.config/pip/pip.conf

echo "📥 Installing python requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found!"
fi

echo "🛠️ Creating systemd service for 24/7 background running..."
SERVICE_FILE="/etc/systemd/system/bot.service"
CURRENT_DIR=$(pwd)

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Vps Discord Bot
After=network.target

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

echo "🔄 Reloading systemd and starting bot service..."
sudo systemctl daemon-reload
sudo systemctl enable bot
sudo systemctl restart bot

echo "✨ Installation and service setup completed successfully!"
