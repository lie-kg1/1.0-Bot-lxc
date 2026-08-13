#!/bin/bash
exec </dev/tty

# Smart path detection to find where .env actually lives
if [ -f ".env" ] && [ ! -d "vps-deploy" ]; then
    ENV_PATH=".env"
else
    ENV_PATH="vps-deploy/.env"
fi

printf "\033[1;36m🤖 ─────────────────────────────────────────\033[0m\n"
printf "\033[1;36m        VPS DEFAULTS CONFIGURATION (EDIT)     \033[0m\n"
printf "\033[1;36m────────────────────────────────────────────\033[0m\n\n"

if [ ! -f "$ENV_PATH" ]; then
    printf "\033[1;31m⚠️ .env file not found! Please run 'create bot' (createbot.sh) first.\033[0m\n"
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

printf "\033[1;33mCurrent values are shown in brackets [ ]. Press Enter to keep current values.\033[0m\n\n"

# ---- Validation helpers ----
validate_size() {
    # matches e.g. 2g, 512m, 10G, 1024M
    [[ "$1" =~ ^[0-9]+[gGmM]$ ]]
}

validate_int() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

validate_hostname() {
    # basic hostname rule: letters, digits, hyphens, 1-63 chars, no leading/trailing hyphen
    [[ "$1" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$ ]]
}

prompt_size() {
    local label="$1" current="$2" __resultvar="$3"
    local input
    while true; do
        read -p "$label [$current]: " input
        input=${input:-$current}
        if validate_size "$input"; then
            printf -v "$__resultvar" '%s' "$input"
            break
        else
            printf "\033[1;31m  ✗ Invalid format. Use a number followed by g/G or m/M, e.g. 2g, 512m.\033[0m\n"
        fi
    done
}

prompt_int() {
    local label="$1" current="$2" __resultvar="$3"
    local input
    while true; do
        read -p "$label [$current]: " input
        input=${input:-$current}
        if validate_int "$input"; then
            printf -v "$__resultvar" '%s' "$input"
            break
        else
            printf "\033[1;31m  ✗ Invalid value. Enter a whole number.\033[0m\n"
        fi
    done
}

prompt_hostname() {
    local label="$1" current="$2" __resultvar="$3"
    local input
    while true; do
        read -p "$label [$current]: " input
        input=${input:-$current}
        if validate_hostname "$input"; then
            printf -v "$__resultvar" '%s' "$input"
            break
        else
            printf "\033[1;31m  ✗ Invalid hostname. Use letters, digits, hyphens only (no leading/trailing hyphen).\033[0m\n"
        fi
    done
}

# ---- Prompts (each validated, re-prompts on bad input) ----
prompt_size    "🧠 Enter Default RAM"              "$CURRENT_RAM"           NEW_RAM
prompt_int     "⚡ Enter Default CPU"               "$CURRENT_CPU"           NEW_CPU
prompt_size    "💾 Enter Default Disk"              "$CURRENT_DISK"          NEW_DISK
prompt_hostname "🌐 Enter VPS Hostname"             "$CURRENT_HOSTNAME"      NEW_HOSTNAME
prompt_int     "📊 Enter Server Limit per user"     "$CURRENT_SERVER_LIMIT"  NEW_SERVER_LIMIT
prompt_int     "📈 Enter Total Server Limit"        "$CURRENT_TOTAL_LIMIT"   NEW_TOTAL_LIMIT

# ---- Safely update or append the values in the .env file ----
# Values are passed via environment variables (not interpolated into the
# Python source) so nothing typed at the prompts can break out of the
# string or run arbitrary code.
ENV_PATH="$ENV_PATH" \
NEW_RAM="$NEW_RAM" \
NEW_CPU="$NEW_CPU" \
NEW_DISK="$NEW_DISK" \
NEW_HOSTNAME="$NEW_HOSTNAME" \
NEW_SERVER_LIMIT="$NEW_SERVER_LIMIT" \
NEW_TOTAL_LIMIT="$NEW_TOTAL_LIMIT" \
python3 -c "
import os

env_path = os.environ['ENV_PATH']
updates = {
    'DEFAULT_RAM': os.environ['NEW_RAM'],
    'DEFAULT_CPU': os.environ['NEW_CPU'],
    'DEFAULT_DISK': os.environ['NEW_DISK'],
    'VPS_HOSTNAME': os.environ['NEW_HOSTNAME'],
    'SERVER_LIMIT': os.environ['NEW_SERVER_LIMIT'],
    'TOTAL_SERVER_LIMIT': os.environ['NEW_TOTAL_LIMIT'],
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

printf "\n\033[1;32m✅ VPS Defaults successfully updated and saved to %s!\033[0m\n" "$ENV_PATH"
