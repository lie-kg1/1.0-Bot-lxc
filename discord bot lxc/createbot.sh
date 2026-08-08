#!/bin/bash

# Smart path detection
if [ -d "vps-deploy" ]; then
    ENV_DIR="vps-deploy"
elif [ -f "bot.py" ] || [ -f "requirements.txt" ]; then
    ENV_DIR="."
else
    ENV_DIR="vps-deploy"
    mkdir -p "$ENV_DIR"
fi

ENV_PATH="$ENV_DIR/.env"

echo "🤖 ──────────────────────────────────────────"
echo "       DISCORD BOT SETUP (CREATE BOT)        "
echo "────────────────────────────────────────────"
echo ""

read -p "🔑  Enter your Discord Bot Token: " BOT_TOKEN
read -p "👤  Enter your Admin Discord User ID: " ADMIN_ID
read -p "🏷️  Enter Bot Status Name [UnixNodes]: " BOT_STATUS
BOT_STATUS=${BOT_STATUS:-UnixNodes}
read -p "💬  Enter Watermark text [Powered by UnixNodes VPS Bot]: " WATERMARK
WATERMARK=${WATERMARK:-Powered by UnixNodes VPS Bot}

echo ""
echo "⚙️  --- VPS DEFAULTS CONFIGURATION ---"
read -p "🧠  Enter Default RAM [2g]: " DEFAULT_RAM
DEFAULT_RAM=${DEFAULT_RAM:-2g}
read -p "⚡  Enter Default CPU [1]: " DEFAULT_CPU
DEFAULT_CPU=${DEFAULT_CPU:-1}
read -p "💾  Enter Default Disk [10G]: " DEFAULT_DISK
DEFAULT_DISK=${DEFAULT_DISK:-10G}
read -p "🌐  Enter VPS Hostname [unix-free]: " VPS_HOSTNAME
VPS_HOSTNAME=${VPS_HOSTNAME:-unix-free}
read -p "📊  Enter Server Limit per user [1]: " SERVER_LIMIT
SERVER_LIMIT=${SERVER_LIMIT:-1}
read -p "📈  Enter Total Server Limit [50]: " TOTAL_SERVER_LIMIT
TOTAL_SERVER_LIMIT=${TOTAL_SERVER_LIMIT:-50}

cat <<EOF > "$ENV_PATH"
TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
BOT_STATUS_NAME=$BOT_STATUS
WATERMARK=$WATERMARK
DEFAULT_RAM=$DEFAULT_RAM
DEFAULT_CPU=$DEFAULT_CPU
DEFAULT_DISK=$DEFAULT_DISK
VPS_HOSTNAME=$VPS_HOSTNAME
SERVER_LIMIT=$SERVER_LIMIT
TOTAL_SERVER_LIMIT=$TOTAL_SERVER_LIMIT
DATABASE_FILE=vps_bot.db
EOF

echo ""
echo "✅  Configuration and VPS Defaults successfully saved to $ENV_PATH!"
echo "🚀  You can now run your bot using: cd $ENV_DIR && python3 bot.py"
