#!/bin/bash
exec </dev/tty

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

printf "\033[1;36m🤖 ─────────────────────────────────────────\033[0m\n"
printf "\033[1;36m        DISCORD BOT SETUP (CREATE BOT)        \033[0m\n"
printf "\033[1;36m────────────────────────────────────────────\033[0m\n\n"

if [ -f "$ENV_PATH" ]; then
    printf "\033[1;33m⚠️ An existing configuration was found at %s\033[0m\n" "$ENV_PATH"
    read -p "Overwrite it? [y/N]: " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        printf "\033[1;33mAborted. Existing configuration left untouched.\033[0m\n"
        exit 0
    fi
    echo
fi

# ---- Validation helpers ----
validate_size() {
    [[ "$1" =~ ^[0-9]+[gGmM]$ ]]
}
validate_int() {
    [[ "$1" =~ ^[0-9]+$ ]]
}
validate_hostname() {
    [[ "$1" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$ ]]
}
validate_discord_id() {
    # Discord snowflake IDs are numeric, typically 17-19 digits
    [[ "$1" =~ ^[0-9]{15,20}$ ]]
}
validate_token_shape() {
    # Loose sanity check: Discord bot tokens are non-empty, no spaces, reasonably long
    [ -n "$1" ] && [[ "$1" != *' '* ]] && [ "${#1}" -ge 20 ]
}

prompt_required() {
    local label="$1" __resultvar="$2" validator="$3" hint="$4"
    local input
    while true; do
        read -p "$label: " input
        if [ -z "$input" ]; then
            printf "\033[1;31m  ✗ This field is required.\033[0m\n"
            continue
        fi
        if [ -n "$validator" ] && ! "$validator" "$input"; then
            printf "\033[1;31m  ✗ %s\033[0m\n" "$hint"
            continue
        fi
        printf -v "$__resultvar" '%s' "$input"
        break
    done
}

prompt_with_default() {
    local label="$1" current="$2" __resultvar="$3" validator="$4" hint="$5"
    local input
    while true; do
        read -p "$label [$current]: " input
        input=${input:-$current}
        if [ -n "$validator" ] && ! "$validator" "$input"; then
            printf "\033[1;31m  ✗ %s\033[0m\n" "$hint"
            continue
        fi
        printf -v "$__resultvar" '%s' "$input"
        break
    done
}

# ---- Bot identity ----
# -s hides the token as it's typed so it doesn't linger in scrollback/screen recordings
read -s -p "🔑  Enter your Discord Bot Token (hidden): " BOT_TOKEN
echo
if ! validate_token_shape "$BOT_TOKEN"; then
    printf "\033[1;31m✗ That doesn't look like a valid bot token (too short or contains spaces). Aborting.\033[0m\n"
    exit 1
fi

prompt_required "👤  Enter your Admin Discord User ID" ADMIN_ID validate_discord_id \
    "Discord IDs are numeric, 15-20 digits. Right-click your user in Discord (Developer Mode on) → Copy User ID."

prompt_with_default "🏷️  Enter Bot Status Name" "UnixNodes" BOT_STATUS "" ""
prompt_with_default "💬  Enter Watermark text" "Powered by UnixNodes VPS Bot" WATERMARK "" ""

printf "\n\033[1;33m⚙️  --- VPS DEFAULTS CONFIGURATION ---\033[0m\n"
prompt_with_default "🧠  Enter Default RAM" "2g" DEFAULT_RAM validate_size \
    "Use a number followed by g/G or m/M, e.g. 2g, 512m."
prompt_with_default "⚡  Enter Default CPU" "1" DEFAULT_CPU validate_int \
    "Enter a whole number."
prompt_with_default "💾  Enter Default Disk" "10G" DEFAULT_DISK validate_size \
    "Use a number followed by g/G or m/M, e.g. 10G, 512m."
prompt_with_default "🌐  Enter VPS Hostname" "unix-free" VPS_HOSTNAME validate_hostname \
    "Use letters, digits, hyphens only (no leading/trailing hyphen)."
prompt_with_default "📊  Enter Server Limit per user" "1" SERVER_LIMIT validate_int \
    "Enter a whole number."
prompt_with_default "📈  Enter Total Server Limit" "50" TOTAL_SERVER_LIMIT validate_int \
    "Enter a whole number."

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

# Restrict permissions since this file contains a live bot token
chmod 600 "$ENV_PATH"

printf "\n\033[1;32m✅  Configuration and VPS Defaults successfully saved to %s!\033[0m\n" "$ENV_PATH"
printf "\033[1;32m🔒  File permissions set to owner-read/write only (chmod 600).\033[0m\n"
printf "\033[1;32m🚀  You can now run your bot using: cd %s && python3 bot.py\033[0m\n" "$ENV_DIR"
