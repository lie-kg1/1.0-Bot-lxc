#!/bin/bash

echo "🚀 Creating and moving to vps-deploy directory..."
mkdir -p vps-deploy
cd vps-deploy || exit

echo "📋 Copying environment configuration..."
if [ -f "test.env" ]; then
    cp test.env .env
    echo "✅ Copied test.env to .env"
else
    echo "⚠️ test.env not found!"
fi

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
