#!/bin/bash

while true; do
    clear
    echo "───────────────────────────────"
    echo "      🚀 DISCORD BOT LXC 🚀    "
    echo "───────────────────────────────"
    echo "1. ⚙️  install"
    echo "2. 📊 create bot"
    echo "3. ⚙️  VPS Defaults"
    echo "4. 🛠️  24/7"
    echo "5. 📁 uninstall"
    echo "6. ❌ Exit"
    echo "───────────────────────────────"
    read -p "Enter your choice [1-5]: " choice

    case $choice in
        1)
            echo "Running install..."
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/install.sh)
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "Running install..."
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/install.sh)
            read -p "Press Enter to continue..."
            ;;    
        3)
            echo "Creating bot..."
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/vpsdefaults.sh)
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "Fixing 24/7..."
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/247.sh)
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Running uninstall..."
            bash <(curl -sL https://raw.githubusercontent.com/lie-kg1/1.0-Bot-lxc/refs/heads/main/uninstall.sh)
            read -p "Press Enter to continue..."
            ;;
        6)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "⚠️ Invalid option. Please choose between 1 and 5."
            sleep 2
            ;;
    esac
done
