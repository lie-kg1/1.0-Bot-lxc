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

while true; do
    clear
    printf "${BLUE}──────────────────────────────────────${NC}\n"
    printf "${CYAN}              BOTPANEL                ${NC}\n"
    printf "${BLUE}──────────────────────────────────────${NC}\n"
    printf "${YELLOW}1)${NC} 📦 Running install\n"
    printf "${YELLOW}2)${NC} ⚙️ Setup .env Configuration File\n"
    printf "${YELLOW}4)${NC} 🚀 Opening 24/7 manager\n"
    printf "${YELLOW}5)${NC} 🗑️ Running uninstall\n"
    printf "${YELLOW}6)${NC} 🌐 Launch botpanel\n"
    printf "${YELLOW}7)${NC} 👋 Exit\n"
    printf "${BLUE}──────────────────────────────────────${NC}\n"
    read -p "Choose an option [1-7]: " choice

    case $choice in
        1)
            printf "${GREEN}Running install...${NC}\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/botpanel/install.sh)
            read -p "Press Enter to continue..."
            ;;
        2)
            printf "${GREEN}Creating bot configuration...${NC}\n"
            bash <(curl -sL "https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/botpanel/Setup%20.env%20Configuration.sh")
            ;;
        4)
            printf "${GREEN}Opening 24/7 manager...${NC}\n"
            bash <(curl -sL "https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/botpanel/Opening%20247%20manager.sh")
            ;;
        5)
            printf "${RED}Running uninstall...${NC}\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/raw/refs/heads/main/botpanel/uninstall.sh)
            read -p "Press Enter to continue..."
            ;;
        6)
            launch_botpanel
            read -p "Press Enter to continue..."
            ;;
        7)
            printf "${CYAN}Exiting...${NC}\n"
            exit 0
            ;;
        *)
            printf "${RED}⚠️ Invalid option. Please choose a valid option.${NC}\n"
            sleep 2
            ;;
    esac
done
