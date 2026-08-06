#!/bin/bash

ENV_DIR="vps-deploy"

while true; do
    clear
    echo "🛠️ =========================================="
    echo "       247 BACKGROUND BOT MANAGER (FIX)      "
    echo "============================================"
    echo ""
    echo "1. 🚀 Start Bot"
    echo "2. 🔄 Restart Bot"
    echo "3. 🛑 Stop Bot"
    echo "4. 📊 24/7 Status & Logs"
    echo "5. ❌ Exit"
    echo "--------------------------------------------"
    read -p "Enter your choice [1-5]: " choice

    if [ ! -d "$ENV_DIR" ]; then
        echo "⚠️ $ENV_DIR directory not found! Please run 'install' first."
        read -p "Press Enter to continue..."
        continue
    fi

    cd "$ENV_DIR" || exit

    case $choice in
        1)
            if pgrep -f "python3 bot.py" > /dev/null; then
                echo "⚠️ Bot is already running!"
            else
                echo "🚀 Starting bot in background..."
                nohup python3 bot.py > bot.log 2>&1 &
                echo "✅ Bot started successfully!"
            fi
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "🔄 Restarting bot..."
            pkill -f "python3 bot.py" 2>/dev/null
            sleep 1
            nohup python3 bot.py > bot.log 2>&1 &
            echo "✅ Bot restarted successfully!"
            read -p "Press Enter to continue..."
            ;;
        3)
            if pgrep -f "python3 bot.py" > /dev/null; then
                echo "🛑 Stopping bot..."
                pkill -f "python3 bot.py"
                echo "✅ Bot stopped successfully!"
            else
                echo "⚠️ Bot is not currently running."
            fi
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "📊 Checking 24/7 status and logs..."
            if pgrep -f "python3 bot.py" > /dev/null; then
                echo "🟢 Status: RUNNING (24/7 background mode active)"
            else
                echo "🔴 Status: STOPPED"
            fi
            echo ""
            echo "--- Last 10 lines of bot.log ---"
            if [ -f "bot.log" ]; then
                tail -n 10 bot.log
            else
                echo "No log file found yet."
            fi
            echo ""
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Exiting manager..."
            exit 0
            ;;
        *)
            echo "❌ Invalid choice! Please enter a number between 1 and 5."
            sleep 2
            ;;
    esac
    cd ..
done
