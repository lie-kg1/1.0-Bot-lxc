#!/bin/bash

while true; do
    clear
    echo "───────────────────────────────"
    echo "      🚀 DISCORD BOT LXC 🚀    "
    echo "───────────────────────────────"
    echo "1. ⚙️ install"
    echo "2. 📊 create bot"
    echo "3. 🛠️ fix 24/7"
    echo "4. 📁 uninstall"
    echo "5. ❌ Exit"
    echo "───────────────────────────────"
    read -p "Enter your choice [1-5]: " choice

    case $choice in
        1)
            echo "Running install..."
            # Add your install commands here
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "Creating bot..."
            # Add your create bot commands here
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "Fixing 24/7..."
            # Add your fix 24/7 commands here
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "Running uninstall..."
            # Add your uninstall commands here
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "⚠️ Invalid option. Please choose between 1 and 5."
            sleep 2
            ;;
    esac
done
