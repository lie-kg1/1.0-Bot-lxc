#!/bin/bash

echo "🚀 Setting up vps-deploy directory..."
mkdir -p vps-deploy

if [ -f "test.env" ]; then
    cp test.env vps-deploy/.env
    echo "✅ Copied test.env to vps-deploy/.env"
else
    echo "⚠️ test.env not found in root!"
fi

if [ -f "requirements.txt" ]; then
    cp requirements.txt vps-deploy/
    echo "✅ Copied requirements.txt to vps-deploy/"
else
    echo "⚠️ requirements.txt not found in root!"
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
