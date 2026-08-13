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

if [ -d "botpanel" ]; then
    cd botpanel
else
    printf "${RED}✗ 'botpanel' directory not found!${NC}\n"
    exit 1
fi

while true; do
    printf "${BLUE}──────────────────────────────────────${NC}\n"
    printf "${CYAN}              BOTPANEL                ${NC}\n"
    printf "${BLUE}──────────────────────────────────────${NC}\n"
    printf "${YELLOW}1)${NC} Install Dependencies (npm install)\n"
    printf "${YELLOW}2)${NC} Start Panel 24/7 (node server.js)\n"
    printf "${YELLOW}3)${NC} Setup .env Configuration File\n"
    printf "${YELLOW}4)${NC} Exit\n"
    printf "${BLUE}──────────────────────────────────────${NC}\n"
    read -p "Choose an option [1-4]: " choice

    case $choice in
        1)
            printf "${YELLOW}📦 Installing Node.js dependencies...${NC}\n"
            npm install
            printf "${GREEN}✅ Installation complete!${NC}\n"
            ;;
        2)
            printf "${GREEN}✨ Starting server.js 24/7...${NC}\n"
            node server.js
            ;;
        3)
            if [ ! -f ".env" ] && [ -f ".env.example" ]; then
                cp .env.example .env
                printf "${GREEN}✅ Created .env file successfully!${NC}\n"
            else
                printf "${YELLOW}⚠️ .env already exists or .env.example is missing.${NC}\n"
            fi
            ;;
        4)
            printf "${CYAN}👋 Exiting menu. Goodbye!${NC}\n"
            exit 0
            ;;
        *)
            printf "${RED}❌ Invalid option. Please choose between 1 and 4.${NC}\n"
            ;;
    esac
    echo ""
done
