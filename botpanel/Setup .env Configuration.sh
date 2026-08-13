#!/bin/bash
set -e

# ANSI Color Codes
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

printf "${BLUE}──────────────────────────────────────${NC}\n"
printf "${CYAN}      SETUP .ENV CONFIGURATION        ${NC}\n"
printf "${BLUE}──────────────────────────────────────${NC}\n"

# Navigate to botpanel directory if it exists
if [ -d "botpanel" ]; then
    cd botpanel
fi

if [ -f ".env" ]; then
    printf "${YELLOW}⚠️ A .env file already exists!${NC}\n"
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [[ "$overwrite" =~ ^[Yy]$ ]]; then
        rm -f .env
    else
        printf "${CYAN}Keeping existing .env file.${NC}\n"
        exit 0
    fi
fi

printf "${YELLOW}⚙️ Creating new .env configuration file...${NC}\n"

cat << 'EOF' > .env
PANEL_PASSWORD=change-me
SESSION_SECRET=change-this-to-a-random-string
PORT=3000
BOT_COMMAND=python3
BOT_ARGS=bot.py
BOT_CWD=./bot
EOF

printf "${GREEN}✅ Successfully created .env file with default settings!${NC}\n"
printf "${YELLOW}💡 Remember to edit botpanel/.env to change your password and settings.${NC}\n"
