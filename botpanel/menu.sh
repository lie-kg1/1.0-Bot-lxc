#!/bin/bash
set -e

printf "\033[1;35m🎮 Welcome to the Botpanel Lobby & Menu\033[0m\n"

# Navigate to botpanel directory
if [ -d "botpanel" ]; then
    cd botpanel
else
    printf "\033[1;31m✗ 'botpanel' directory not found!\033[0m\n"
    exit 1
fi

while true; do
    echo "======================================"
    echo "          BOTPANEL  MENU         "
    echo "======================================"
    echo "1) Install Dependencies (npm install)"
    echo "2) Start Panel 24/7 (node server.js)"
    echo "3) Setup .env Configuration File"
    echo "4) Exit"
    echo "======================================"
    read -p "Choose an option [1-4]: " choice

    case $choice in
        1)
            printf "\033[1;33m📦 Installing Node.js dependencies...\033[0m\n"
            npm install
            printf "\033[1;32m✅ Installation complete!\033[0m\n"
            ;;
        2)
            printf "\033[1;32m✨ Starting server.js 24/7...\033[0m\n"
            node server.js
            ;;
        3)
            if [ ! -f ".env" ] && [ -f ".env.example" ]; then
                cp .env.example .env
                printf "\033[1;32m✅ Created .env file successfully!\033[0m\n"
            else
                printf "\033[1;33m⚠️ .env already exists or .env.example is missing.\033[0m\n"
            fi
            ;;
        4)
            printf "\033[1;36m👋 Exiting menu. Goodbye!\033[0m\n"
            exit 0
            ;;
        *)
            printf "\033[1;31m❌ Invalid option. Please choose between 1 and 4.\033[0m\n"
            ;;
    esac
    echo ""
done
