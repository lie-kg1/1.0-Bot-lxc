#!/bin/bash

ENV_DIR="vps-deploy"
ENV_PATH="$ENV_DIR/.env"

echo "🤖 =========================================="
echo "       DISCORD BOT SETUP (CREATE BOT)        "
echo "============================================"
echo ""

# Ensure vps-deploy directory exists
mkdir -p "$ENV_DIR"

# Prompt user for configuration inputs
read -p "Enter your Discord Bot Token: " BOT_TOKEN
read -p "Enter your Admin Discord User ID: " ADMIN_ID
read -p "Enter Bot Status Name [UnixNodes]: " BOT_STATUS
BOT_STATUS=${BOT_STATUS:-UnixNodes}
read -p "Enter Watermark text [Powered by UnixNodes VPS Bot]: " WATERMARK
WATERMARK=${WATERMARK:-Powered by UnixNodes VPS Bot}

# Write configuration cleanly to the .env file
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
echo "✅ Configuration successfully saved to $ENV_PATH!"
echo "🚀 You can now run your bot using: cd vps-deploy && python3 bot.py"
