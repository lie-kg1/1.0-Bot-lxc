#!/bin/bash
set -e

# ANSI Color Codes
CYAN='\033[1;36m'
MAGENTA='\033[1;35m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;34m'
NC='\033[0m' # No Color

printf "${BLUE}──────────────────────────────────────${NC}\n"
printf "${CYAN}        COMPLETE INSTALL SCRIPT       ${NC}\n"
printf "${BLUE}──────────────────────────────────────${NC}\n"

# Navigate to botpanel directory if it exists
if [ -d "botpanel" ]; then
    cd botpanel
    printf "${GREEN}📁 Entered botpanel directory.${NC}\n"
else
    printf "${RED}✗ 'botpanel' directory not found! Please run this from the root folder.${NC}\n"
    exit 1
fi

# 1. Install Node.js dependencies
printf "${YELLOW}📦 Installing npm dependencies...${NC}\n"
npm install
printf "${GREEN}✅ Dependencies installed successfully!${NC}\n"

# 2. Setup .env configuration file automatically if missing
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        printf "${GREEN}✅ Created .env file from .env.example${NC}\n"
    else
        printf "${YELLOW}⚠️ .env.example not found, creating a default .env file...${NC}\n"
        cat << 'EOF' > .env
PANEL_PASSWORD=change-me
SESSION_SECRET=change-this-to-a-random-string
PORT=3000
BOT_COMMAND=python3
BOT_ARGS=bot.py
BOT_CWD=./bot
EOF
        printf "${GREEN}✅ Default .env file created successfully!${NC}\n"
    fi
else
    printf "${CYAN}ℹ️ .env file already exists, skipping creation.${NC}\n"
fi

printf "${GREEN}🎉 All installation steps completed successfully!${NC}\n"
