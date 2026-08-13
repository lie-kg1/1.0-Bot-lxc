#!/bin/bash

# Where botpanel lives on this machine. Adjust if you cloned it elsewhere.
BOTPANEL_DIR="${BOTPANEL_DIR:-$HOME/1.0-Bot-lxc/botpanel}"
BOTPANEL_REPO="https://github.com/lie-kg1/1.0-Bot-lxc.git"

launch_botpanel() {
    if [ ! -d "$BOTPANEL_DIR" ]; then
        printf "\033[1;33mbotpanel not found at %s\033[0m\n" "$BOTPANEL_DIR"
        read -p "Clone the repo now to fetch it? [y/N]: " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            git clone "$BOTPANEL_REPO" "$(dirname "$BOTPANEL_DIR")"/.. 2>/dev/null || \
            git clone "$BOTPANEL_REPO" "$HOME/1.0-Bot-lxc"
        else
            printf "\033[1;31mCannot launch botpanel without it present.\033[0m\n"
            return 1
        fi
    fi

    cd "$BOTPANEL_DIR" || { printf "\033[1;31mCould not enter %s\033[0m\n" "$BOTPANEL_DIR"; return 1; }

    if [ ! -d "node_modules" ]; then
        printf "\033[1;32mInstalling botpanel dependencies (first run)...\033[0m\n"
        npm install
    fi

    if [ ! -f ".env" ]; then
        printf "\033[1;33mNo .env found — copying .env.example.\033[0m\n"
        printf "\033[1;33mEdit %s/.env to set a real PANEL_PASSWORD before exposing this.\033[0m\n" "$BOTPANEL_DIR"
        cp .env.example .env
    fi

    printf "\033[1;32mStarting botpanel...\033[0m\n"
    printf "\033[1;36mOpen http://<this-server-ip>:3000 in your browser once it's up.\033[0m\n"
    npm start
}

while true; do
    clear
    printf "\033[1;36m───────────────────────────────\033[0m\n"
    printf "\033[1;32m    🚀  DISCORD BOT LXC 🚀      \033[0m\n"
    printf "\033[1;36m───────────────────────────────\033[0m\n"
    printf "\033[1;33m1.\033[0m ⚙️ install\n"
    printf "\033[1;33m2.\033[0m 📊 create bot\n"
    printf "\033[1;33m3.\033[0m ⚙️ VPS Defaults\n"
    printf "\033[1;33m4.\033[0m 🛠️ 24/7 Manager\n"
    printf "\033[1;33m5.\033[0m 📁 uninstall\n"
    printf "\033[1;33m6.\033[0m 🌐 Bot Panel\n"
    printf "\033[1;33m7.\033[0m ❌ Exit\n"
    printf "\033[1;36m───────────────────────────────\033[0m\n"
    read -p "Enter your choice [1-7]: " choice
    case $choice in
        1)
            printf "\033[1;32mRunning install...\033[0m\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/install.sh)
            read -p "Press Enter to continue..."
            ;;
        2)
            printf "\033[1;32mCreating bot configuration...\033[0m\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/createbot.sh)
            read -p "Press Enter to continue..."
            ;;
        3)
            printf "\033[1;32mConfiguring VPS Defaults...\033[0m\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/vpsdefaults.sh)
            read -p "Press Enter to continue..."
            ;;
        4)
            printf "\033[1;32mOpening 24/7 manager...\033[0m\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/247.sh)
            read -p "Press Enter to continue..."
            ;;
        5)
            printf "\033[1;31mRunning uninstall...\033[0m\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/uninstall.sh)
            read -p "Press Enter to continue..."
            ;;
        6)
            printf "\033[1;32mBot Panel...\033[0m\n"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/Bot-Panel/refs/heads/main/Bot-Panel/Bot%20Panel.sh)
            read -p "Press Enter to continue..."
            ;;
        7)
            printf "\033[1;31mExiting...\033[0m\n"
            exit 0
            ;;
        *)
            printf "\033[1;31m⚠️ Invalid option. Please choose between 1 and 7.\033[0m\n"
            sleep 2
            ;;
    esac
done
