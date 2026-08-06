#!/bin/bash

ENV_DIR="vps-deploy"
SERVICE_FILE="/etc/systemd/system/bot.service"

echo "🗑️  =========================================="
echo "       DISCORD BOT UNINSTALLER               "
echo "============================================"
echo ""

# Stop any running bot instances
echo "🛑  Stopping any running bot processes..."
pkill -f "python3 bot.py" 2>/dev/null

# Remove systemd service if it exists
if [ -f "$SERVICE_FILE" ]; then
    echo "⚙️  Removing systemd bot service..."
    sudo systemctl stop bot 2>/dev/null
    sudo systemctl disable bot 2>/dev/null
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
fi

# Remove deployment directory
if [ -d "$ENV_DIR" ]; then
    echo "📁  Removing $ENV_DIR directory and configurations..."
    rm -rf "$ENV_DIR"
else
    echo "⚠️  $ENV_DIR directory not found."
fi

echo ""
echo "✨  Uninstallation completed successfully! All bot files, databases, and background services have been removed."
