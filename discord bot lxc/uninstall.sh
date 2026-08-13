#!/bin/bash
exec </dev/tty

ENV_DIR="vps-deploy"
SERVICE_FILE="/etc/systemd/system/bot.service"

printf "\033[1;36m🗑️ ─────────────────────────────────────────\033[0m\n"
printf "\033[1;36m         DISCORD BOT UNINSTALLER             \033[0m\n"
printf "\033[1;36m────────────────────────────────────────────\033[0m\n\n"

printf "\033[1;31mThis will permanently:\033[0m\n"
printf "  • Stop and remove the systemd 'bot' service (if present)\n"
printf "  • Kill any running 'python3 bot.py' processes\n"
printf "  • Delete the '%s/' directory and everything in it\n" "$ENV_DIR"
printf "  • Delete bot.pid, bot.log, vps_bot.db, test.env, requirements.txt, and bot.py from this folder\n\n"

read -p "Type 'yes' to confirm and continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    printf "\033[1;33mAborted. Nothing was removed.\033[0m\n"
    exit 0
fi

echo

# Stop any running bot instances (matches this project's launch command specifically)
printf "\033[1;33m🛑 Stopping any running bot processes...\033[0m\n"
pkill -f "python3[[:space:]]\+bot\.py" 2>/dev/null

# Clean up local PID or background artifacts if they exist in current root folder
if [ -f "vps-deploy/bot.pid" ]; then
    PID=$(cat vps-deploy/bot.pid 2>/dev/null)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
    fi
fi
if [ -f "bot.pid" ]; then
    PID=$(cat bot.pid 2>/dev/null)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
    fi
fi

# Remove systemd service if it exists
if [ -f "$SERVICE_FILE" ]; then
    printf "\033[1;33m⚙️ Removing systemd bot service...\033[0m\n"
    if command -v sudo >/dev/null 2>&1; then
        sudo systemctl stop bot 2>/dev/null || true
        sudo systemctl disable bot 2>/dev/null || true
        sudo rm -f "$SERVICE_FILE"
        sudo systemctl daemon-reload
    else
        printf "\033[1;31m⚠️ 'sudo' not available — skipping systemd service removal. Remove %s manually if needed.\033[0m\n" "$SERVICE_FILE"
    fi
fi

# Remove deployment directory
if [ -d "$ENV_DIR" ]; then
    printf "\033[1;31m📁 Removing %s directory and configurations...\033[0m\n" "$ENV_DIR"
    rm -rf "$ENV_DIR"
else
    printf "\033[1;33m⚠️ %s directory not found.\033[0m\n" "$ENV_DIR"
fi

# Clear out orphaned runtime files/databases from workspace root
printf "\033[1;31m🧹 Cleaning up residual workspace files...\033[0m\n"
rm -f bot.pid bot.log vps_bot.db test.env requirements.txt bot.py

printf "\n\033[1;32m✨ Uninstallation completed successfully! All bot files, databases, and background services have been removed.\033[0m\n"
