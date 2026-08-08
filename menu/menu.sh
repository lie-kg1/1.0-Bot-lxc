#!/bin/bash

while true; do
    clear
    echo -e "\033[1;36m───────────────────────────────\033[0m"
    echo -e "\033[1;32m    🚀  DISCORD BOT LXC 🚀     \033[0m"
    echo -e "\033[1;36m───────────────────────────────\033[0m"
    echo -e "\033[1;33m1.\033[0m ⚙️  install"
    echo -e "\033[1;33m2.\033[0m 📊  create bot"
    echo -e "\033[1;33m3.\033[0m ⚙️  VPS Defaults"
    echo -e "\033[1;33m4.\033[0m 🛠️  24/7 Manager"
    echo -e "\033[1;33m5.\033[0m 📁  uninstall"
    echo -e "\033[1;33m6.\033[0m ❌  Exit"
    echo -e "\033[1;36m───────────────────────────────\033[0m"
    read -p "Enter your choice [1-6]: " choice

    case $choice in
        1)
            echo -e "\033[1;32mRunning install...\033[0m"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/install.sh)
            read -p "Press Enter to continue..."
            ;;
        2)
            echo -e "\033[1;32mCreating bot configuration...\033[0m"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/createbot.sh)
            read -p "Press Enter to continue..."
            ;;    
        3)
            echo -e "\033[1;32mConfiguring VPS Defaults...\033[0m"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/vpsdefaults.sh)
            read -p "Press Enter to continue..."
            ;;
        4)
            echo -e "\033[1;32mOpening 24/7 manager...\033[0m"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/247.sh)
            read -p "Press Enter to continue..."
            ;;
        5)
            echo -e "\033[1;31mRunning uninstall...\033[0m"
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/discord%20bot%20lxc/uninstall.sh)
            read -p "Press Enter to continue..."
            ;;
        6)
            echo -e "\033[1;31mExiting...\033[0m"
            exit 0
            ;;
        *)
            echo -e "\033[1;31m⚠️ Invalid option. Please choose between 1 and 6.\033[0m"
            sleep 2
            ;;
    esac
done
