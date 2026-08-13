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
printf "${RED}         BOTPANEL UNINSTALLER         ${NC}\n"
printf "${BLUE}──────────────────────────────────────${NC}\n"

printf "${YELLOW}⚠️ Warning: This will remove the botpanel directory and all of its local data/configurations.${NC}\n"
read -p "Are you sure you want to uninstall? (y/N): " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    if [ -d "botpanel" ]; then
        printf "${RED}🗑️ Removing botpanel directory...${NC}\n"
        rm -rf botpanel
        printf "${GREEN}✅ Successfully uninstalled botpanel.${NC}\n"
    else
        printf "${YELLOW}ℹ️ 'botpanel' directory not found in the current path.${NC}\n"
    fi
else
    printf "${CYAN}❌ Uninstall cancelled.${NC}\n"
fi
