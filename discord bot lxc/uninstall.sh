#!/bin/bash
exec </dev/tty

ENV_DIR="vps-deploy"
SERVICE_FILE="/etc/systemd/system/bot.service"

printf "\033[1;36m🗑️  ─────────────────────────────────────────\033[0m\n"
printf "\033[1;36m        DISCORD BOT UNINSTALLER             \033[0m\n"
printf "\033[1;36m────────────────────────────────────────────\033[0m\n\n"

# Stop any running bot instances
printf "\033[1;33m🛑 Stopping any running bot processes...\033[0m\n"
pkill -f "python3 bot.py" 2>/dev/null

# Clean up local PID or background artifacts if they exist in current root folder
if [ -f "vps-deploy/bot.pid" ]; then
    kill "$(cat vps-deploy/bot.pid)" 2>/dev/null || true
fi
if [ -f "bot.pid" ]; then
    kill "$(cat bot.pid)" 2>/dev/null || true
fi

# Remove systemd service if it exists
if [ -f "$SERVICE_FILE" ]; then
    printf "\033[1;33m⚙️ Removing systemd bot service...\033[0m\n"
    sudo systemctl stop bot 2>/dev/null || true
    sudo systemctl disable bot 2>/dev/null || true
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
fi

# Remove deployment directory
if [ -d "$ENV_DIR" ]; then
    printf "\033[1;31m📁 Removing $ENV_DIR directory and configurations...\033[0m\n"
    rm -rf "$ENV_DIR"
else
    printf "\033[1;33m⚠️ $ENV_DIR directory not found.\033[0m\n"
fi

# FIXED: Clear out orphaned runtime files/databases from workspace root
printf "\033[1;31m🧹 Cleaning up residual workspace files...\033[0m\n"
rm -f bot.pid bot.log vps_bot.db test.env requirements.txt bot.py

printf "\n\033[1;32m✨ Uninstallation completed successfully! All bot files, databases, and background services have been removed.\033[0m\n"
