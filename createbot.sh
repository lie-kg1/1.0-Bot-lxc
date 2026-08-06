#!/bin/bash

ENV_PATH="vps-deploy/.env"

echo "🤖 === DISCORD BOT CONFIGURATION (CREATE BOT) ==="
echo ""

if [ ! -f "$ENV_PATH" ]; then
    echo "⚠️ .env file not found in vps-deploy/! Creating a new one..."
    mkdir -p vps-deploy
    touch "$ENV_PATH"
fi

read -p "Enter your Discord Bot Token: " BOT_TOKEN
read -p "Enter your Admin Discord User ID: " ADMIN_ID
read -p "Enter Bot Status Name [UnixNodes]: " BOT_STATUS
BOT_STATUS=${BOT_STATUS:-UnixNodes}
read -p "Enter Watermark text [Powered by UnixNodes VPS Bot]: " WATERMARK
WATERMARK=${WATERMARK:-Powered by UnixNodes VPS Bot}

# Update or write to .env file
cat <<EOF > "$ENV_PATH"
# Discord Bot Token (from Discord Developer Portal)
TOKEN=$BOT_TOKEN

# Admin Discord User ID (get from Discord Developer Mode)
ADMIN_ID=$ADMIN_ID

# Bot Configuration
BOT_STATUS_NAME=$BOT_STATUS
WATERMARK=$WATERMARK

# VPS Defaults
DEFAULT_RAM=2g
DEFAULT_CPU=1
DEFAULT_DISK=10G
VPS_HOSTNAME=unix-free
SERVER_LIMIT=1
TOTAL_SERVER_LIMIT=50

# Database
DATABASE_FILE=vps_bot.db
EOF

echo ""
echo "✅ Configuration saved successfully to $ENV_PATH!"
echo "🚀 You can now start or restart your bot."
