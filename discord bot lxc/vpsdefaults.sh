#!/bin/bash

ENV_DIR="vps-deploy"
ENV_PATH="$ENV_DIR/.env"

echo "🤖  ─────────────────────────────────────────"
echo "       VPS DEFAULTS CONFIGURATION (EDIT)     "
echo "────────────────────────────────────────────"
echo ""

if [ ! -f "$ENV_PATH" ]; then
    echo "⚠️  .env file not found in $ENV_DIR/! Please run 'create bot' first."
    exit 1
fi

# Read current values from .env if they exist
CURRENT_RAM=$(grep "^DEFAULT_RAM=" "$ENV_PATH" | cut -d '=' -f2)
CURRENT_CPU=$(grep "^DEFAULT_CPU=" "$ENV_PATH" | cut -d '=' -f2)
CURRENT_DISK=$(grep "^DEFAULT_DISK=" "$ENV_PATH" | cut -d '=' -f2)
CURRENT_HOSTNAME=$(grep "^VPS_HOSTNAME=" "$ENV_PATH" | cut -d '=' -f2)
CURRENT_SERVER_LIMIT=$(grep "^SERVER_LIMIT=" "$ENV_PATH" | cut -d '=' -f2)
CURRENT_TOTAL_LIMIT=$(grep "^TOTAL_SERVER_LIMIT=" "$ENV_PATH" | cut -d '=' -f2)

CURRENT_RAM=${CURRENT_RAM:-2g}
CURRENT_CPU=${CURRENT_CPU:-1}
CURRENT_DISK=${CURRENT_DISK:-10G}
CURRENT_HOSTNAME=${CURRENT_HOSTNAME:-unix-free}
CURRENT_SERVER_LIMIT=${CURRENT_SERVER_LIMIT:-1}
CURRENT_TOTAL_LIMIT=${CURRENT_TOTAL_LIMIT:-50}

echo "Current values are shown in brackets [ ]. Press Enter to keep current values."
echo ""

read -p "🧠  Enter Default RAM [$CURRENT_RAM]: " NEW_RAM
NEW_RAM=${NEW_RAM:-$CURRENT_RAM}

read -p "⚡  Enter Default CPU [$CURRENT_CPU]: " NEW_CPU
NEW_CPU=${NEW_CPU:-$CURRENT_CPU}

read -p "💾  Enter Default Disk [$CURRENT_DISK]: " NEW_DISK
NEW_DISK=${NEW_DISK:-$CURRENT_DISK}

read -p "🌐  Enter VPS Hostname [$CURRENT_HOSTNAME]: " NEW_HOSTNAME
NEW_HOSTNAME=${NEW_HOSTNAME:-$CURRENT_HOSTNAME}

read -p "📊  Enter Server Limit per user [$CURRENT_SERVER_LIMIT]: " NEW_SERVER_LIMIT
NEW_SERVER_LIMIT=${NEW_SERVER_LIMIT:-$CURRENT_SERVER_LIMIT}

read -p "📈  Enter Total Server Limit [$CURRENT_TOTAL_LIMIT]: " NEW_TOTAL_LIMIT
NEW_TOTAL_LIMIT=${NEW_TOTAL_LIMIT:-$CURRENT_TOTAL_LIMIT}

# Safely update or append the values in the .env file using Python
python3 -c "
import os

env_path = '$ENV_PATH'
updates = {
    'DEFAULT_RAM': '$NEW_RAM',
    'DEFAULT_CPU': '$NEW_CPU',
    'DEFAULT_DISK': '$NEW_DISK',
    'VPS_HOSTNAME': '$NEW_HOSTNAME',
    'SERVER_LIMIT': '$NEW_SERVER_LIMIT',
    'TOTAL_SERVER_LIMIT': '$NEW_TOTAL_LIMIT'
}

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        lines = f.readlines()
else:
    lines = []

updated_keys = set()
new_lines = []
for line in lines:
    stripped = line.strip()
    if '=' in stripped and not stripped.startswith('#'):
        key = stripped.split('=')[0].strip()
        if key in updates:
            new_lines.append(f'{key}={updates[key]}\n')
            updated_keys.add(key)
            continue
    new_lines.append(line)

for key, val in updates.items():
    if key not in updated_keys:
        new_lines.append(f'{key}={val}\n')

with open(env_path, 'w') as f:
    f.writelines(new_lines)
"

echo ""
echo "✅  VPS Defaults successfully updated and saved to $ENV_PATH!"
